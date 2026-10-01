"""Pre-merge self-improvement flywheel workflow and mathlore PR merging."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import shutil
import tempfile
import time
import uuid

from sqlalchemy.orm import Session

from mathlore_forge.agents.mathlingua_agent import create_mathlingua_agent
from mathlore_forge.agents.reflection_agent import ReflectionAgent
from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.mlg.client import MlgClient
from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    ReviewCommentRecord,
    RunStatus,
    RunType,
)
from mathlore_forge.storage.gcs_sync import sync_db_to_gcs_now
from mathlore_forge.tools.git_tools import GitWorkspace
from mathlore_forge.workflows.github_client import GitHubClient

logger = logging.getLogger(__name__)


class FlywheelFlow:
    """Orchestrates pre-merge validation, self-healing, reflection, forge improvement PR, and mathlore PR merge."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        config: MathloreConfig | None = None,
    ):
        self.github_client = github_client or GitHubClient()
        self.config = config or load_config()
        self.reflection_agent = ReflectionAgent(config=self.config)

    def _create_workspace(self, repo: str, prefix: str) -> tuple[GitWorkspace, Path]:
        """Creates an isolated git workspace for the target repository."""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        if "mathlore-forge" not in repo:
            local_mathlore = self.config.paths.mathlore_repo
            if local_mathlore and Path(local_mathlore).is_dir():
                workspace = GitWorkspace.init_from_existing(local_mathlore, temp_dir)
                return workspace, temp_dir
        else:
            forge_root = Path(__file__).resolve().parent.parent.parent.parent
            if (forge_root / "skills").is_dir():
                workspace = GitWorkspace.init_from_existing(forge_root, temp_dir)
                return workspace, temp_dir

        repo_url = f"https://github.com/{repo}.git"
        if self.github_client.token:
            repo_url = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
        workspace = GitWorkspace.clone(repo_url, temp_dir)
        return workspace, temp_dir

    async def execute(
        self,
        mathlore_repo: str,
        pr_number: int,
        db_session: Session,
        forge_repo: str = "mathlingua/mathlore-forge",
        run_id: str | None = None,
        dashboard_url: str | None = None,
    ) -> AgentRunRecord:
        """Executes the pre-merge quality gates, flywheel improvement, and PR merge."""
        run_id = run_id or f"run_flywheel_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Fetch GitHub PR details first
        gh_pr = await self.github_client.get_pull_request(mathlore_repo, pr_number)
        head_branch = gh_pr.head_branch

        # 2. Fetch PR & Issue records from DB
        pr_record = (
            db_session.query(PullRequestRecord)
            .filter_by(repo=mathlore_repo, pr_number=pr_number)
            .first()
        )
        issue_id = pr_record.issue_id if pr_record else None
        issue_record = db_session.query(IssueRecord).filter_by(id=issue_id).first() if issue_id else None

        if not issue_record:
            m = re.search(r"issue-(\d+)", head_branch) or re.search(
                r"(?:Closes|Resolves|Fixes)\s+#(\d+)", gh_pr.body, re.IGNORECASE
            )
            if m:
                inferred_num = int(m.group(1))
                issue_record = (
                    db_session.query(IssueRecord)
                    .filter_by(repo=mathlore_repo, issue_number=inferred_num)
                    .first()
                )

        # 3. Create run record
        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.FLYWHEEL_IMPROVEMENT,
            status=RunStatus.RUNNING,
            repo=forge_repo,
            pr_id=pr_record.id if pr_record else None,
            pr_number=pr_number,
            branch_name=head_branch,
            prompt=f"Acceptance, pre-merge validation, and flywheel improvement from mathlore PR #{pr_number}",
        )
        db_session.add(run_record)
        db_session.commit()

        # Check if PR is already merged
        if gh_pr.merged:
            if pr_record:
                pr_record.status = "MERGED"
            if issue_record:
                issue_record.status = "RESOLVED"
                issue_record.plan_status = "COMPLETED"

            prior_runs = (
                db_session.query(AgentRunRecord)
                .filter(
                    (AgentRunRecord.pr_number == pr_number) |
                    ((AgentRunRecord.issue_id == issue_record.id) if issue_record else False)
                )
                .filter(AgentRunRecord.status.in_([RunStatus.AWAITING_REVIEW, RunStatus.RUNNING, RunStatus.ADDRESSING_COMMENTS, RunStatus.QUEUED]))
                .all()
            )
            for r in prior_runs:
                r.status = RunStatus.COMPLETED
                if not r.completed_at:
                    r.completed_at = datetime.now(timezone.utc)

            run_record.status = RunStatus.COMPLETED
            run_record.summary = f"Pull request #{pr_number} is already merged."
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.duration_seconds = time.perf_counter() - start_time
            db_session.commit()
            sync_db_to_gcs_now()
            return run_record

        # 4. Post immediate acknowledgment comment on PR
        dash_link = f"[View Run on Mathlore Forge Dashboard]({dashboard_url})" if dashboard_url else ""
        ack_comment = (
            f"### 🤖 Mathlore Forge: PR Acceptance Received\n\n"
            f"I have received your acceptance of PR #{pr_number} and am executing pre-merge quality gates.\n\n"
            f"- **Run ID**: `{run_id}`\n"
            f"- **Branch**: `{head_branch}`\n"
            + (f"- **Live Dashboard & Telemetry**: {dash_link}\n" if dash_link else "")
            + f"\n*Validating syntax and semantics via `mlg check`, self-healing any errors, and waiting for CI checks before merging.*"
        )
        try:
            await self.github_client.create_issue_comment(
                repo=mathlore_repo,
                issue_or_pr_number=pr_number,
                body=ack_comment,
            )
        except Exception as ack_err:
            logger.warning("Could not post acceptance acknowledgment on %s#%s: %s", mathlore_repo, pr_number, ack_err)

        flywheel_pr_url = ""
        mathlore_temp_dir: Path | None = None
        try:
            # 5. Pre-merge validation & self-healing on mathlore branch
            mathlore_workspace, mathlore_temp_dir = self._create_workspace(
                mathlore_repo, f"forge_merge_check_{run_id}_"
            )
            mathlore_workspace.checkout_branch(head_branch)

            mlg_bin = self.config.resolve_mlg_bin()
            mlg_client = MlgClient(content_root=mathlore_workspace.workspace_dir, mlg_bin=mlg_bin)

            report = mlg_client.check(json_output=True)
            if not report.successful or report.issue_count > 0:
                logger.info(
                    "Pre-merge validation found %d issues on %s branch %s. Triggering self-healing agent.",
                    report.issue_count,
                    mathlore_repo,
                    head_branch,
                )

                agent = create_mathlingua_agent(
                    content_root=mathlore_workspace.workspace_dir,
                    skills_dir=self.config.resolve_skills_dir(),
                    mlg_bin=mlg_bin,
                    model=self.config.models.author,
                    config=self.config,
                )

                fix_prompt = (
                    f"Pre-merge verification check reported compiler diagnostics on PR #{pr_number} (branch `{head_branch}`):\n\n"
                    f"```\n{report.summary()}\n```\n\n"
                    f"### Instructions\n"
                    f"1. Locate and inspect each diagnostic and affected `.mlg` file.\n"
                    f"2. Fix all syntax, structural, and semantic compiler errors.\n"
                    f"3. Run `mlg_check` to confirm 0 diagnostics.\n"
                    f"4. Run `mlg_format`.\n"
                    f"5. Summarize the exact changes made to resolve each error."
                )

                async with agent:
                    fix_response = await agent.chat(fix_prompt)
                    fix_summary = await fix_response.text()

                if mathlore_workspace.has_changes():
                    commit_msg = f"[Forge] Auto-fix mlg check compiler errors before merge on PR #{pr_number}"
                    mathlore_workspace.commit(commit_msg)
                    if self.github_client.token:
                        auth_origin = f"https://x-access-token:{self.github_client.token}@github.com/{mathlore_repo}.git"
                        mathlore_workspace.run_git(["remote", "set-url", "origin", auth_origin], check=False)
                    mathlore_workspace.push("origin", head_branch)

                    fix_notice = (
                        f"### 🛠️ Automated Pre-Merge Diagnostics Resolution\n\n"
                        f"During pre-merge verification, `mlg check` detected compiler issues:\n"
                        f"> {report.summary()}\n\n"
                        f"The Mathlore Forge authoring agent automatically resolved the diagnostics and pushed a new commit to `{head_branch}`.\n\n"
                        f"#### Summary of Changes:\n"
                        f"{fix_summary.strip()}"
                    )
                    await self.github_client.create_issue_comment(
                        repo=mathlore_repo,
                        issue_or_pr_number=pr_number,
                        body=fix_notice,
                    )

                # Re-check to confirm it is clean
                post_fix_report = mlg_client.check(json_output=True)
                if not post_fix_report.successful or post_fix_report.issue_count > 0:
                    fail_msg = (
                        f"### ⚠️ Pre-Merge Check Failed\n\n"
                        f"`mlg check` still reports errors after automated self-healing attempt:\n\n"
                        f"```\n{post_fix_report.summary()}\n```\n\n"
                        f"Automatic merge paused. Please review the errors or comment `/forge address`."
                    )
                    await self.github_client.create_issue_comment(
                        repo=mathlore_repo,
                        issue_or_pr_number=pr_number,
                        body=fail_msg,
                    )
                    run_record.status = RunStatus.FAILED
                    run_record.error_message = f"mlg check failed pre-merge: {post_fix_report.summary()}"
                    return run_record

            # 6. Wait for GitHub status checks / check runs to pass
            gh_pr = await self.github_client.get_pull_request(mathlore_repo, pr_number)
            head_ref = gh_pr.head_sha or gh_pr.head_branch

            checks_passed, checks_msg = await self.github_client.wait_for_checks_to_pass(
                repo=mathlore_repo,
                ref=head_ref,
                timeout_seconds=300,
                poll_interval=5,
            )

            if not checks_passed:
                fail_checks_msg = (
                    f"### ⚠️ Pre-Merge Checks Blocked\n\n"
                    f"Cannot merge PR #{pr_number} because GitHub status checks did not succeed:\n"
                    f"> {checks_msg}\n\n"
                    f"Automatic merge aborted. Once checks pass, re-run with `/forge accept`."
                )
                await self.github_client.create_issue_comment(
                    repo=mathlore_repo,
                    issue_or_pr_number=pr_number,
                    body=fail_checks_msg,
                )
                run_record.status = RunStatus.FAILED
                run_record.error_message = checks_msg
                return run_record

            # 7. Collect review comments and run flywheel self-improvement if comments exist
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

            if comments_data:
                learning = await self.reflection_agent.analyze_feedback(comments_data)

                forge_temp_dir: Path | None = None
                try:
                    forge_workspace, forge_temp_dir = self._create_workspace(
                        forge_repo, f"forge_flywheel_{run_id}_"
                    )
                    branch_name = f"forge/improve-from-mathlore-pr-{pr_number}"
                    forge_workspace.checkout_branch(branch_name, create=True)

                    modified_files = self.reflection_agent.apply_learning_to_forge(
                        forge_workspace.workspace_dir,
                        learning,
                    )

                    if forge_workspace.has_changes():
                        commit_msg = (
                            f"[Flywheel] Learn from Dominic Kramer's feedback on mathlore PR #{pr_number}\n\n"
                            f"- Added guideline: {learning.get('guideline_text', '')}\n"
                            f"- Created golden test: {learning.get('golden_test_id', '')}"
                        )
                        forge_workspace.commit(commit_msg)

                        try:
                            if self.github_client.token:
                                auth_origin = f"https://x-access-token:{self.github_client.token}@github.com/{forge_repo}.git"
                                forge_workspace.run_git(["remote", "set-url", "origin", auth_origin], check=False)
                            forge_workspace.push("origin", branch_name)
                        except Exception:
                            pass

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
                            logger.warning("Failed opening forge PR: %s", err)
                finally:
                    if forge_temp_dir and forge_temp_dir.exists():
                        shutil.rmtree(forge_temp_dir, ignore_errors=True)

            # 8. Merge the mathlore PR
            merge_success = await self.github_client.merge_pull_request(
                repo=mathlore_repo,
                pr_number=pr_number,
                commit_title=f"Merge pull request #{pr_number} from {head_branch}",
            )

            if merge_success:
                if pr_record:
                    pr_record.status = "MERGED"
                close_comment = (
                    f"Successfully authored, reviewed, and merged in PR #{pr_number}!\n"
                    + (f"Self-improvement PR created in mathlore-forge: {flywheel_pr_url}" if flywheel_pr_url else "")
                )
                if issue_record:
                    issue_record.status = "RESOLVED"
                    issue_record.plan_status = "COMPLETED"
                    try:
                        await self.github_client.close_issue(
                            repo=mathlore_repo,
                            issue_number=issue_record.issue_number,
                            comment=close_comment,
                        )
                    except Exception as close_err:
                        logger.warning(
                            "Could not close originating issue %s#%s: %s",
                            mathlore_repo,
                            issue_record.issue_number,
                            close_err,
                        )

                # Mark all previous runs for this PR / issue that are AWAITING_REVIEW (or active) as COMPLETED
                prior_runs = (
                    db_session.query(AgentRunRecord)
                    .filter(
                        (AgentRunRecord.pr_number == pr_number) |
                        ((AgentRunRecord.issue_id == issue_record.id) if issue_record else False)
                    )
                    .filter(AgentRunRecord.status.in_([RunStatus.AWAITING_REVIEW, RunStatus.RUNNING, RunStatus.ADDRESSING_COMMENTS, RunStatus.QUEUED]))
                    .all()
                )
                for r in prior_runs:
                    r.status = RunStatus.COMPLETED
                    if not r.completed_at:
                        r.completed_at = datetime.now(timezone.utc)

                pr_final_comment = (
                    f"### ✅ Pull Request Accepted & Merged\n\n"
                    f"All pre-merge validation checks passed successfully. PR #{pr_number} has been merged into `main`.\n\n"
                    + (f"- **Self-Improvement**: [View Forge PR]({flywheel_pr_url})\n" if flywheel_pr_url else "")
                    + (f"- Originating issue #{issue_record.issue_number} has been closed.\n" if issue_record else "")
                )
                try:
                    await self.github_client.create_issue_comment(
                        repo=mathlore_repo,
                        issue_or_pr_number=pr_number,
                        body=pr_final_comment,
                    )
                except Exception:
                    pass

                run_record.status = RunStatus.COMPLETED
                run_record.summary = (
                    f"Successfully validated, self-healed, and merged mathlore PR #{pr_number}. "
                    + (f"Self-improvement PR opened: {flywheel_pr_url}" if flywheel_pr_url else "No review comments to learn from.")
                )
            else:
                run_record.status = RunStatus.FAILED
                run_record.error_message = f"GitHub API failed to merge PR #{pr_number}"
                try:
                    await self.github_client.create_issue_comment(
                        repo=mathlore_repo,
                        issue_or_pr_number=pr_number,
                        body=f"### ⚠️ Merge Failed\n\nGitHub API returned an error attempting to merge PR #{pr_number}. Please check for merge conflicts.",
                    )
                except Exception:
                    pass

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            raise
        finally:
            if mathlore_temp_dir and mathlore_temp_dir.exists():
                shutil.rmtree(mathlore_temp_dir, ignore_errors=True)
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)
            db_session.commit()
            sync_db_to_gcs_now()

        return run_record
