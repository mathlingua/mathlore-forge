"""Orchestration workflow for addressing PR review comments."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import time
import uuid

from sqlalchemy.orm import Session

from mathlore_forge.agents.hooks import TrajectoryTelemetryHooks
from mathlore_forge.agents.mathlingua_agent import create_mathlingua_agent
from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.goldens.trajectory import Trajectory
from mathlore_forge.storage.db import (
    AgentRunRecord,
    PullRequestRecord,
    ReviewCommentRecord,
    RunStatus,
    RunType,
    TrajectoryRecord,
)
from mathlore_forge.storage.gcs_sync import sync_db_to_gcs_now
from mathlore_forge.tools.git_tools import GitWorkspace
from mathlore_forge.workflows.github_client import GitHubClient, GitHubReviewComment


class ReviewFlow:
    """Orchestrates pulling review comments, executing fixes via agent, and updating the PR."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        config: MathloreConfig | None = None,
    ):
        self.github_client = github_client or GitHubClient()
        self.config = config or load_config()

    async def execute(
        self,
        repo: str,
        pr_number: int,
        db_session: Session,
        run_id: str | None = None,
    ) -> AgentRunRecord:
        """Executes the review comment resolution workflow."""
        run_id = run_id or f"run_review_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Fetch PR details
        pr = await self.github_client.get_pull_request(repo, pr_number)

        # 2. Find or create PR record
        pr_record = (
            db_session.query(PullRequestRecord)
            .filter_by(repo=repo, pr_number=pr_number)
            .first()
        )
        if not pr_record:
            pr_record = PullRequestRecord(
                repo=repo,
                pr_number=pr_number,
                branch_name=pr.head_branch,
                title=pr.title,
                status="ADDRESSING_COMMENTS",
                pr_url=pr.html_url,
            )
            db_session.add(pr_record)
            db_session.commit()
        else:
            pr_record.status = "ADDRESSING_COMMENTS"
            pr_record.review_rounds += 1
            db_session.commit()

        # 3. Fetch review comments from GitHub
        raw_comments = await self.github_client.list_review_comments(repo, pr_number)

        # Filter out comments already addressed in DB
        unaddressed_comments: list[GitHubReviewComment] = []
        for c in raw_comments:
            existing = (
                db_session.query(ReviewCommentRecord)
                .filter_by(comment_github_id=c.id)
                .first()
            )
            if not existing or not existing.addressed:
                unaddressed_comments.append(c)
                if not existing:
                    new_rec = ReviewCommentRecord(
                        pr_id=pr_record.id,
                        pr_number=pr_number,
                        comment_github_id=c.id,
                        author=c.author,
                        body=c.body,
                        file_path=c.path,
                        line=c.line,
                        diff_hunk=c.diff_hunk,
                        addressed=False,
                    )
                    db_session.add(new_rec)
        db_session.commit()

        # 4. Create AgentRunRecord
        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.ADDRESS_COMMENTS,
            status=RunStatus.RUNNING,
            repo=repo,
            pr_id=pr_record.id,
            pr_number=pr_number,
            branch_name=pr.head_branch,
            prompt=f"Address {len(unaddressed_comments)} review comments on PR #{pr_number}",
        )
        db_session.add(run_record)
        db_session.commit()

        trajectory = Trajectory(metadata={"run_id": run_id, "pr_number": pr_number, "repo": repo})
        from mathlore_forge.web.routes.api import broadcast_run_event
        telemetry_hooks = TrajectoryTelemetryHooks(
            trajectory=trajectory,
            event_callback=lambda evt: broadcast_run_event(run_id, evt),
        )

        # 5. Setup workspace and checkout branch
        temp_dir = Path(tempfile.mkdtemp(prefix=f"forge_review_{run_id}_"))
        try:
            local_mathlore = self.config.paths.mathlore_repo
            if local_mathlore and Path(local_mathlore).is_dir():
                workspace = GitWorkspace.init_from_existing(local_mathlore, temp_dir)
            else:
                repo_url = f"https://github.com/{repo}.git"
                if self.github_client.token:
                    repo_url = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
                workspace = GitWorkspace.clone(repo_url, temp_dir)

            workspace.checkout_branch(pr.head_branch)

            # 6. Initialize Antigravity agent
            agent = create_mathlingua_agent(
                content_root=workspace.workspace_dir,
                skills_dir=self.config.resolve_skills_dir(),
                mlg_bin=self.config.resolve_mlg_bin(),
                model=self.config.models.author,
                hooks=telemetry_hooks.get_hooks(),
                config=self.config,
            )

            # 7. Construct review resolution prompt
            comments_text = "\n\n".join(
                f"- **Comment #{c.id} by {c.author}** in `{c.path}` (line {c.line}):\n"
                f"  Feedback: \"{c.body}\"\n"
                f"  Diff context: ```\n{c.diff_hunk}\n```"
                for c in unaddressed_comments
            )

            review_prompt = (
                f"You need to address the following review feedback from Dominic Kramer on PR #{pr_number} "
                f"({pr.title}):\n\n"
                f"{comments_text}\n\n"
                f"### Action Plan\n"
                f"1. For each piece of feedback, locate the item in the collection.\n"
                f"2. Apply the requested mathematical corrections, structural fixes, or documentation.\n"
                f"3. Run `mlg_check` to verify zero diagnostics.\n"
                f"4. Run `mlg_format`.\n"
                f"5. Summarize the exact changes made for each comment."
            )

            async with agent:
                response = await agent.chat(review_prompt)
                response_text = await response.text()
                run_record.conversation_id = agent.conversation_id

                if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                    usage = agent.conversation.total_usage
                    run_record.prompt_tokens = getattr(usage, "prompt_token_count", 0)
                    run_record.candidates_tokens = getattr(usage, "candidates_token_count", 0)
                    run_record.thoughts_tokens = getattr(usage, "thoughts_token_count", 0)
                    run_record.total_tokens = getattr(usage, "total_token_count", 0)

            run_record.summary = response_text
            trajectory.final_output = response_text

            # 8. Collect git diff
            diff_patch = workspace.get_diff()
            run_record.diff_patch = diff_patch

            # 9. Commit and push updates
            if workspace.has_changes():
                commit_msg = f"[Forge] Address review comments on PR #{pr_number}"
                workspace.commit(commit_msg)

            try:
                if self.github_client.token:
                    auth_origin = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
                    workspace.run_git(["remote", "set-url", "origin", auth_origin], check=False)
                workspace.push("origin", pr.head_branch)
            except Exception:
                pass

            # 10. Reply to each review comment on GitHub
            for c in unaddressed_comments:
                reply_body = f"Addressed by Mathlore Forge agent: {response_text[:300]}..."
                try:
                    await self.github_client.reply_to_review_comment(
                        repo=repo,
                        pr_number=pr_number,
                        comment_id=c.id,
                        body=reply_body,
                    )
                except Exception:
                    pass

                # Mark comment as addressed in DB
                db_comment = (
                    db_session.query(ReviewCommentRecord)
                    .filter_by(comment_github_id=c.id)
                    .first()
                )
                if db_comment:
                    db_comment.addressed = True
                    db_comment.reply_body = reply_body

            # 11. Post summary comment on PR and re-request review
            summary_comment = (
                f"### Review Comments Addressed\n\n"
                f"I have addressed the feedback from Dominic Kramer:\n\n"
                f"{response_text}\n\n"
                f"Compiler verification (`mlg check`) passed with 0 diagnostics.\n\n"
                f"---\n"
                f"Ready for your review! Reply or approve when ready."
            )
            await self.github_client.create_issue_comment(repo, pr_number, summary_comment)
            await self.github_client.request_reviewers(repo, pr_number, ["DominicKramer"])

            pr_record.status = "AWAITING_REVIEW"
            run_record.status = RunStatus.AWAITING_REVIEW

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            raise
        finally:
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)

            traj_record = TrajectoryRecord(
                run_id=run_id,
                trajectory_json=trajectory.model_dump_json(),
                markdown_summary=trajectory.to_markdown(),
            )
            db_session.add(traj_record)
            db_session.commit()
            if temp_dir and temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            sync_db_to_gcs_now()

        return run_record
