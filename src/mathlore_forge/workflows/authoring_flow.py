"""Orchestration workflow for initial issue authoring and PR creation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import re
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
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    RunType,
    TrajectoryRecord,
)
from mathlore_forge.tools.git_tools import GitWorkspace
from mathlore_forge.workflows.github_client import GitHubClient, GitHubIssue, GitHubPullRequest


def slugify(text: str) -> str:
    """Converts a title into a clean git branch slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:40] or "task"


class AuthoringFlow:
    """Orchestrates checkout, authoring, testing, and PR creation for an issue."""

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
        issue_number: int,
        db_session: Session,
        run_id: str | None = None,
        workspace_base_dir: Path | str | None = None,
    ) -> AgentRunRecord:
        """Executes the full authoring workflow for a GitHub issue."""
        run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Fetch issue details
        issue = await self.github_client.get_issue(repo, issue_number)

        # 2. Persist issue record
        issue_record = (
            db_session.query(IssueRecord)
            .filter_by(repo=repo, issue_number=issue_number)
            .first()
        )
        if not issue_record:
            issue_record = IssueRecord(
                repo=repo,
                issue_number=issue_number,
                title=issue.title,
                body=issue.body,
                author=issue.author,
                status="IN_PROGRESS",
            )
            db_session.add(issue_record)
            db_session.commit()

        # 3. Create initial AgentRunRecord
        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.INITIAL_AUTHORING,
            status=RunStatus.RUNNING,
            repo=repo,
            issue_id=issue_record.id,
            issue_number=issue_number,
            prompt=f"Author content for issue #{issue_number}: {issue.title}\n\n{issue.body}",
        )
        db_session.add(run_record)
        db_session.commit()

        trajectory = Trajectory(metadata={"run_id": run_id, "issue_number": issue_number, "repo": repo})
        telemetry_hooks = TrajectoryTelemetryHooks(trajectory=trajectory)

        # 4. Setup isolated git workspace
        temp_dir = Path(tempfile.mkdtemp(prefix=f"forge_run_{run_id}_"))
        slug = slugify(issue.title)
        branch_name = f"forge/issue-{issue_number}-{slug}"
        run_record.branch_name = branch_name

        try:
            # Clone or copy target repo
            local_mathlore = self.config.paths.mathlore_repo
            if local_mathlore and Path(local_mathlore).is_dir():
                workspace = GitWorkspace.init_from_existing(local_mathlore, temp_dir)
            else:
                repo_url = f"https://github.com/{repo}.git"
                workspace = GitWorkspace.clone(repo_url, temp_dir)

            workspace.checkout_branch(branch_name, create=True)

            # 5. Initialize Antigravity authoring agent targeting workspace
            agent = create_mathlingua_agent(
                content_root=workspace.workspace_dir,
                skills_dir=self.config.resolve_skills_dir(),
                mlg_bin=self.config.resolve_mlg_bin(),
                model=self.config.models.author,
                hooks=telemetry_hooks.get_hooks(),
                config=self.config,
            )

            # 6. Run agent authoring turn
            authoring_prompt = (
                f"You are authoring Mathlingua content to resolve the following issue:\n\n"
                f"### Issue #{issue_number}: {issue.title}\n"
                f"{issue.body}\n\n"
                f"### Instructions\n"
                f"1. Inspect the collection structure and locate the appropriate file.\n"
                f"2. Formulate and insert the required mathematical items.\n"
                f"3. Run `mlg_check` to validate and generate UUIDs. Fix any compiler errors.\n"
                f"4. Run `mlg_format` to format the modified files.\n"
                f"5. Provide a clear summary of the changes made and mathematical references."
            )

            async with agent:
                response = await agent.chat(authoring_prompt)
                response_text = await response.text()
                conversation_id = agent.conversation_id
                run_record.conversation_id = conversation_id

                # Collect token usage
                if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                    usage = agent.conversation.total_usage
                    run_record.prompt_tokens = getattr(usage, "prompt_token_count", 0)
                    run_record.candidates_tokens = getattr(usage, "candidates_token_count", 0)
                    run_record.thoughts_tokens = getattr(usage, "thoughts_token_count", 0)
                    run_record.total_tokens = getattr(usage, "total_token_count", 0)

            run_record.summary = response_text
            trajectory.final_output = response_text

            # 7. Collect git diff
            diff_patch = workspace.get_diff(base_ref="HEAD~1" if not workspace.has_changes() else None)
            if not diff_patch and workspace.has_changes():
                diff_patch = workspace.get_diff()
            run_record.diff_patch = diff_patch

            # 8. Commit and push changes
            if workspace.has_changes():
                commit_msg = f"[Forge] {issue.title} (closes #{issue_number})"
                workspace.commit(commit_msg)

            # Push branch if remote configured
            try:
                workspace.push("origin", branch_name)
            except Exception:
                pass  # In local test environments without remote origin, continue

            # 9. Open Pull Request on GitHub
            pr_title = f"[Forge] {issue.title} (closes #{issue_number})"
            pr_body = (
                f"### Autonomous Mathlore Authoring\n\n"
                f"Resolves #{issue_number}.\n\n"
                f"#### Summary of Changes\n"
                f"{response_text}\n\n"
                f"---\n"
                f"*Authored by Mathlore Forge with Google Antigravity Agent Harness.*"
            )

            try:
                pr = await self.github_client.create_pull_request(
                    repo=repo,
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main",
                )
                run_record.pr_number = pr.number
                run_record.status = RunStatus.AWAITING_REVIEW

                # Create PR record
                pr_record = PullRequestRecord(
                    repo=repo,
                    pr_number=pr.number,
                    branch_name=branch_name,
                    title=pr_title,
                    issue_id=issue_record.id,
                    status="AWAITING_REVIEW",
                    pr_url=pr.html_url,
                )
                db_session.add(pr_record)

                # Request review from Dominic
                await self.github_client.request_reviewers(repo, pr.number, [issue.author])
                await self.github_client.create_issue_comment(
                    repo,
                    pr.number,
                    f"@{issue.author} The initial Mathlingua authoring is complete! Please review the PR and leave feedback. "
                    f"When ready, leave a review or comment `/forge address` to trigger any requested modifications.",
                )
            except Exception as pr_err:
                run_record.error_message = f"PR creation warning: {pr_err}"
                run_record.status = RunStatus.AWAITING_REVIEW

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            raise
        finally:
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)

            # Persist trajectory
            traj_record = TrajectoryRecord(
                run_id=run_id,
                trajectory_json=trajectory.model_dump_json(),
                markdown_summary=trajectory.to_markdown(),
            )
            db_session.add(traj_record)
            db_session.commit()

        return run_record
