"""Pre-merge self-improvement flywheel workflow and mathlore PR merging."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import uuid

from sqlalchemy.orm import Session

from mathlore_forge.agents.reflection_agent import ReflectionAgent
from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    ReviewCommentRecord,
    RunStatus,
    RunType,
)
from mathlore_forge.tools.git_tools import GitWorkspace
from mathlore_forge.workflows.github_client import GitHubClient


class FlywheelFlow:
    """Orchestrates pre-merge reflection, forge improvement PR, and mathlore PR merge."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        config: MathloreConfig | None = None,
    ):
        self.github_client = github_client or GitHubClient()
        self.config = config or load_config()
        self.reflection_agent = ReflectionAgent(config=self.config)

    async def execute(
        self,
        mathlore_repo: str,
        pr_number: int,
        db_session: Session,
        forge_repo: str = "mathlingua/mathlore-forge",
        run_id: str | None = None,
    ) -> AgentRunRecord:
        """Executes the pre-merge flywheel improvement and PR merge."""
        run_id = run_id or f"run_flywheel_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Fetch PR record
        pr_record = (
            db_session.query(PullRequestRecord)
            .filter_by(repo=mathlore_repo, pr_number=pr_number)
            .first()
        )
        issue_id = pr_record.issue_id if pr_record else None
        issue_record = db_session.query(IssueRecord).filter_by(id=issue_id).first() if issue_id else None

        # 2. Collect review comments
        comments = (
            db_session.query(ReviewCommentRecord)
            .filter_by(pr_number=pr_number)
            .all()
        )
        comments_data = [
            {
                "id": c.comment_github_id,
                "author": c.author,
                "body": c.body,
                "path": c.file_path,
                "line": c.line,
                "diff_hunk": c.diff_hunk,
            }
            for c in comments
        ]

        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.FLYWHEEL_IMPROVEMENT,
            status=RunStatus.RUNNING,
            repo=forge_repo,
            pr_id=pr_record.id if pr_record else None,
            pr_number=pr_number,
            prompt=f"Pre-merge reflection and forge improvement from mathlore PR #{pr_number}",
        )
        db_session.add(run_record)
        db_session.commit()

        flywheel_pr_url = ""
        try:
            # 3. If there were review comments, synthesize learnings & open PR in mathlore-forge
            if comments_data:
                learning = await self.reflection_agent.analyze_feedback(comments_data)

                # Setup workspace for mathlore-forge
                temp_dir = Path(tempfile.mkdtemp(prefix=f"forge_flywheel_{run_id}_"))
                forge_root = Path(__file__).resolve().parent.parent.parent.parent
                if (forge_root / "skills").is_dir():
                    workspace = GitWorkspace.init_from_existing(forge_root, temp_dir)
                else:
                    workspace = GitWorkspace.clone(f"https://github.com/{forge_repo}.git", temp_dir)

                branch_name = f"forge/improve-from-mathlore-pr-{pr_number}"
                workspace.checkout_branch(branch_name, create=True)

                # Apply learned guideline to skills and generate golden test
                modified_files = self.reflection_agent.apply_learning_to_forge(
                    workspace.workspace_dir,
                    learning,
                )

                if workspace.has_changes():
                    commit_msg = (
                        f"[Flywheel] Learn from Dominic Kramer's feedback on mathlore PR #{pr_number}\n\n"
                        f"- Added guideline: {learning.get('guideline_text', '')}\n"
                        f"- Created golden test: {learning.get('golden_test_id', '')}"
                    )
                    workspace.commit(commit_msg)

                    try:
                        workspace.push("origin", branch_name)
                    except Exception:
                        pass

                    # Open PR in mathlore-forge
                    forge_pr_title = f"[Flywheel] Improvements from mathlore PR #{pr_number}"
                    forge_pr_body = (
                        f"### Autonomous Self-Improvement Flywheel\n\n"
                        f"Extracted learnings from Dominic Kramer's review on `mathlore` PR #{pr_number}.\n\n"
                        f"#### Synthesized Guideline\n"
                        f"> {learning.get('guideline_text', '')}\n\n"
                        f"#### Golden Test Added\n"
                        f"`golden_tests/{learning.get('golden_test_id', '')}`\n\n"
                        f"Files modified: {', '.join(str(f.name) for f in modified_files)}\n\n"
                        f"---\n"
                        f"*Submitted by Mathlore Forge Self-Improvement Engine.*"
                    )

                    try:
                        forge_pr = await self.github_client.create_pull_request(
                            repo=forge_repo,
                            title=forge_pr_title,
                            body=forge_pr_body,
                            head=branch_name,
                            base="main",
                        )
                        flywheel_pr_url = forge_pr.html_url
                        await self.github_client.request_reviewers(
                            forge_repo,
                            forge_pr.number,
                            ["DominicKramer"],
                        )
                    except Exception as err:
                        run_record.error_message = f"Failed opening forge PR: {err}"

            # 4. Merge the mathlore PR
            merge_success = await self.github_client.merge_pull_request(
                repo=mathlore_repo,
                pr_number=pr_number,
                commit_title=f"Merge pull request #{pr_number} from {pr_record.branch_name if pr_record else 'forge'}",
            )

            if merge_success:
                if pr_record:
                    pr_record.status = "MERGED"
                if issue_record:
                    issue_record.status = "RESOLVED"
                    close_comment = (
                        f"Successfully authored, reviewed, and merged in PR #{pr_number}!\n"
                        + (f"Self-improvement PR created in mathlore-forge: {flywheel_pr_url}" if flywheel_pr_url else "")
                    )
                    await self.github_client.close_issue(
                        repo=mathlore_repo,
                        issue_number=issue_record.issue_number,
                        comment=close_comment,
                    )

                run_record.status = RunStatus.COMPLETED
                run_record.summary = (
                    f"Successfully merged mathlore PR #{pr_number}. "
                    + (f"Self-improvement PR opened: {flywheel_pr_url}" if flywheel_pr_url else "No review comments to learn from.")
                )
            else:
                run_record.status = RunStatus.FAILED
                run_record.error_message = f"GitHub API failed to merge PR #{pr_number}"

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            raise
        finally:
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)
            db_session.commit()

        return run_record
