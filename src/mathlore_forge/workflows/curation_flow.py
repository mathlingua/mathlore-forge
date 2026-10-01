"""Curation, planning, and plan-execution workflow orchestrator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import shutil
import tempfile
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from mathlore_forge.agents.curator_agent import CuratorAgent
from mathlore_forge.agents.hooks import TrajectoryTelemetryHooks
from mathlore_forge.agents.mathlingua_agent import create_mathlingua_agent
from mathlore_forge.config import MathloreConfig, load_config
from mathlore_forge.goldens.trajectory import Trajectory
from mathlore_forge.observability.notifications import NotificationService
from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    RunType,
    TrajectoryRecord,
)
from mathlore_forge.storage.gcs_sync import sync_db_to_gcs_now
from mathlore_forge.tools.git_tools import GitWorkspace
from mathlore_forge.workflows.authoring_flow import slugify
from mathlore_forge.workflows.github_client import GitHubClient, GitHubIssue


class CurationFlow:
    """Manages high-order planning proposals, interactive refinements, and plan execution."""

    def __init__(
        self,
        github_client: GitHubClient | None = None,
        curator_agent: CuratorAgent | None = None,
        notification_service: NotificationService | None = None,
        config: MathloreConfig | None = None,
    ):
        self.config = config or load_config()
        self.github_client = github_client or GitHubClient()
        self._curator_agent_override = curator_agent
        self.notification_service = notification_service or NotificationService()

    @property
    def curator_agent(self) -> CuratorAgent:
        """Returns the curator agent instance, falling back to a default if configured."""
        if self._curator_agent_override:
            return self._curator_agent_override
        return CuratorAgent(config=self.config)

    def _create_workspace(self, repo: str, prefix: str) -> tuple[GitWorkspace, Path]:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        local_mathlore = self.config.paths.mathlore_repo
        if local_mathlore and Path(local_mathlore).is_dir():
            workspace = GitWorkspace.init_from_existing(local_mathlore, temp_dir)
        else:
            repo_url = f"https://github.com/{repo}.git"
            if self.github_client.token:
                repo_url = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
            workspace = GitWorkspace.clone(repo_url, temp_dir)
        return workspace, temp_dir

    async def _recover_plan_from_github(self, repo: str, issue_number: int) -> str | None:
        """Recovers the most recent proposal text from GitHub issue comments if DB was reset."""
        comments = await self.github_client.list_issue_comments(repo, issue_number)
        for c in reversed(comments):
            body = c.get("body", "")
            if "## 📋 Mathlore Proposal" in body or "### 📋 Mathlore Proposal" in body:
                idx = body.find("## 📋 Mathlore Proposal")
                if idx == -1:
                    idx = body.find("### 📋 Mathlore Proposal")
                return body[idx:].strip()
        return None

    async def handle_initial_proposal(
        self,
        repo: str,
        issue_number: int,
        issue_title: str,
        issue_body: str,
        db_session: Session,
        author: str = "DominicKramer",
        run_id: str | None = None,
        dashboard_url: str | None = None,
    ) -> str:
        """Formulates an initial proposal and posts it to the GitHub issue."""
        run_id = run_id or f"run_plan_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # 1. Persist or fetch IssueRecord
        issue_record = (
            db_session.query(IssueRecord)
            .filter_by(repo=repo, issue_number=issue_number)
            .first()
        )
        if not issue_record:
            issue_record = IssueRecord(
                repo=repo,
                issue_number=issue_number,
                title=issue_title,
                body=issue_body,
                author=author,
                status="PLANNING",
                plan_status="PLANNING",
            )
            db_session.add(issue_record)
            db_session.commit()
        else:
            issue_record.plan_status = "PLANNING"
            db_session.commit()

        # 2. Record AgentRunRecord
        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.CURATION_PLANNING,
            status=RunStatus.RUNNING,
            repo=repo,
            issue_id=issue_record.id,
            issue_number=issue_number,
            prompt=f"Draft architectural proposal for issue #{issue_number}: {issue_title}\n\n{issue_body}",
        )
        db_session.add(run_record)
        db_session.commit()

        temp_dir: Path | None = None
        try:
            # 3. Formulate proposal via Curator Agent targeting a real cloned repository workspace
            if self._curator_agent_override:
                curator = self._curator_agent_override
            else:
                workspace, temp_dir = self._create_workspace(repo, f"forge_plan_{run_id}_")
                curator = CuratorAgent(content_root=workspace.workspace_dir, config=self.config)

            raw_proposal = await curator.draft_proposal(
                issue_title=issue_title,
                issue_body=issue_body,
            )

            # Strip any pre-tool diagnostic notices or system error messages
            idx = raw_proposal.find("## 📋 Mathlore Proposal")
            if idx != -1:
                proposal = raw_proposal[idx:].strip()
            else:
                proposal = raw_proposal.strip()

            # 4. Update IssueRecord
            issue_record.plan_markdown = proposal
            issue_record.plan_status = "AWAITING_APPROVAL"
            issue_record.plan_revision = 1
            issue_record.status = "AWAITING_PLAN_APPROVAL"
            db_session.commit()

            # 5. Post proposal to GitHub issue
            proposal_body = proposal
            if dashboard_url:
                proposal_body = (
                    f"{proposal}\n\n"
                    f"---\n"
                    f"🔍 **Telemetry & Compiler Logs**: [View Run `{run_id}` on Mathlore Forge Dashboard]({dashboard_url})\n\n"
                    f"💬 *Next Steps:* Comment on this issue to refine the plan, or comment `/forge execute` to approve and begin authoring."
                )
            await self.github_client.create_issue_comment(
                repo=repo,
                issue_or_pr_number=issue_number,
                body=proposal_body,
            )

            # 6. Notify Dominic Kramer
            self.notification_service.notify_plan_ready(
                repo=repo,
                issue_number=issue_number,
                issue_title=issue_title,
                revision=1,
            )

            run_record.status = RunStatus.COMPLETED
            run_record.summary = proposal

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            db_session.commit()
            raise
        finally:
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)
            db_session.commit()
            if temp_dir and temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            sync_db_to_gcs_now()

        return proposal

    async def handle_proposal_refinement(
        self,
        repo: str,
        issue_number: int,
        user_feedback: str,
        db_session: Session,
        run_id: str | None = None,
        dashboard_url: str | None = None,
    ) -> str:
        """Refines the proposal based on Dominic Kramer's issue comments."""
        run_id = run_id or f"run_refine_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        issue_record = (
            db_session.query(IssueRecord)
            .filter_by(repo=repo, issue_number=issue_number)
            .first()
        )
        if not issue_record or not issue_record.plan_markdown:
            logger.info("Plan not found in DB for %s#%s; attempting recovery from GitHub issue comments", repo, issue_number)
            plan_text = await self._recover_plan_from_github(repo, issue_number)
            if plan_text:
                gh_issue = await self.github_client.get_issue(repo, issue_number)
                if not issue_record:
                    issue_record = IssueRecord(
                        repo=repo,
                        issue_number=issue_number,
                        title=gh_issue.title,
                        body=gh_issue.body,
                        author=gh_issue.author,
                        status="PLANNING",
                        plan_status="AWAITING_APPROVAL",
                        plan_markdown=plan_text,
                        plan_revision=1,
                    )
                    db_session.add(issue_record)
                else:
                    issue_record.plan_markdown = plan_text
                    issue_record.plan_status = "AWAITING_APPROVAL"
                    issue_record.plan_revision = issue_record.plan_revision or 1
                db_session.commit()
            else:
                raise ValueError(f"No active proposal found for {repo}#{issue_number} to refine.")

        current_revision = issue_record.plan_revision or 1
        new_revision = current_revision + 1

        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.CURATION_PLANNING,
            status=RunStatus.RUNNING,
            repo=repo,
            issue_id=issue_record.id,
            issue_number=issue_number,
            prompt=f"Refine proposal (Revision {new_revision}) for issue #{issue_number} based on feedback:\n{user_feedback}",
        )
        db_session.add(run_record)
        db_session.commit()

        temp_dir: Path | None = None
        try:
            # Refine proposal via Curator Agent targeting cloned repository workspace
            if self._curator_agent_override:
                curator = self._curator_agent_override
            else:
                workspace, temp_dir = self._create_workspace(repo, f"forge_refine_{run_id}_")
                curator = CuratorAgent(content_root=workspace.workspace_dir, config=self.config)

            raw_refined = await curator.refine_proposal(
                current_proposal=issue_record.plan_markdown,
                revision=new_revision,
                user_feedback=user_feedback,
            )

            idx = raw_refined.find("## 📋 Mathlore Proposal")
            if idx != -1:
                refined = raw_refined[idx:].strip()
            else:
                refined = raw_refined.strip()

            issue_record.plan_markdown = refined
            issue_record.plan_revision = new_revision
            issue_record.plan_status = "AWAITING_APPROVAL"
            db_session.commit()

            # Post updated proposal
            body_to_post = refined
            if dashboard_url:
                body_to_post = (
                    f"{refined}\n\n"
                    f"---\n"
                    f"🔍 **Telemetry & Compiler Logs**: [View Run `{run_id}` on Mathlore Forge Dashboard]({dashboard_url})\n\n"
                    f"💬 *Next Steps:* Comment on this issue to refine further, or comment `/forge execute` to approve and begin authoring."
                )
            await self.github_client.create_issue_comment(
                repo=repo,
                issue_or_pr_number=issue_number,
                body=body_to_post,
            )

            # Notify Dominic
            self.notification_service.notify_plan_ready(
                repo=repo,
                issue_number=issue_number,
                issue_title=issue_record.title,
                revision=new_revision,
            )

            run_record.status = RunStatus.COMPLETED
            run_record.summary = refined

        except Exception as exc:
            run_record.status = RunStatus.FAILED
            run_record.error_message = str(exc)
            db_session.commit()
            raise
        finally:
            run_record.duration_seconds = time.perf_counter() - start_time
            run_record.completed_at = datetime.now(timezone.utc)
            db_session.commit()
            if temp_dir and temp_dir.is_dir():
                shutil.rmtree(temp_dir, ignore_errors=True)
            sync_db_to_gcs_now()

        return refined

    async def handle_plan_execution(
        self,
        repo: str,
        issue_number: int,
        db_session: Session,
        run_id: str | None = None,
        dashboard_url: str | None = None,
    ) -> AgentRunRecord:
        """Executes an approved plan by spawning authoring agent(s) and creating the PR."""
        run_id = run_id or f"run_exec_{uuid.uuid4().hex[:12]}"
        dash_link = dashboard_url or "https://mathlore-forge-web-bx7vyixa6a-uc.a.run.app"
        start_time = time.perf_counter()

        issue_record = (
            db_session.query(IssueRecord)
            .filter_by(repo=repo, issue_number=issue_number)
            .first()
        )
        if not issue_record or not issue_record.plan_markdown:
            logger.info("Plan not found in DB for %s#%s; attempting recovery from GitHub issue comments", repo, issue_number)
            plan_text = await self._recover_plan_from_github(repo, issue_number)
            if plan_text:
                gh_issue = await self.github_client.get_issue(repo, issue_number)
                if not issue_record:
                    issue_record = IssueRecord(
                        repo=repo,
                        issue_number=issue_number,
                        title=gh_issue.title,
                        body=gh_issue.body,
                        author=gh_issue.author,
                        status="PLANNING",
                        plan_status="AWAITING_APPROVAL",
                        plan_markdown=plan_text,
                        plan_revision=1,
                    )
                    db_session.add(issue_record)
                else:
                    issue_record.plan_markdown = plan_text
                    issue_record.plan_status = "AWAITING_APPROVAL"
                    issue_record.plan_revision = issue_record.plan_revision or 1
                db_session.commit()
            else:
                raise ValueError(f"No approved plan found for issue {repo}#{issue_number}.")

        issue_record.plan_status = "APPROVED"
        issue_record.status = "EXECUTING_PLAN"
        db_session.commit()

        # Acknowledge on GitHub
        await self.github_client.create_issue_comment(
            repo=repo,
            issue_or_pr_number=issue_number,
            body=(
                f"### 🚀 Plan Approved by @DominicKramer\n\n"
                f"Launching autonomous authoring agent to execute Revision {issue_record.plan_revision} of the plan.\n"
                f"The agent will create files, register them in `toc` tables of contents, validate with `mlg check`, and open a Pull Request.\n\n"
                f"Track live execution progress on the dashboard: [View Run on Mathlore Forge Dashboard]({dash_link})"
            ),
        )
        self.notification_service.notify_plan_approved(
            repo=repo,
            issue_number=issue_number,
            issue_title=issue_record.title,
        )

        slug = slugify(issue_record.title)
        branch_name = f"forge/curation-issue-{issue_number}-{slug}"

        run_record = AgentRunRecord(
            id=run_id,
            run_type=RunType.PLAN_EXECUTION,
            status=RunStatus.RUNNING,
            repo=repo,
            issue_id=issue_record.id,
            issue_number=issue_number,
            branch_name=branch_name,
            prompt=f"Execute approved plan for #{issue_number}: {issue_record.title}\n\n{issue_record.plan_markdown}",
        )
        db_session.add(run_record)
        db_session.commit()

        trajectory = Trajectory(metadata={"run_id": run_id, "issue_number": issue_number, "repo": repo})
        telemetry_hooks = TrajectoryTelemetryHooks(trajectory=trajectory)

        # Setup isolated git workspace
        temp_dir = Path(tempfile.mkdtemp(prefix=f"forge_exec_{run_id}_"))
        try:
            local_mathlore = self.config.paths.mathlore_repo
            if local_mathlore and Path(local_mathlore).is_dir():
                workspace = GitWorkspace.init_from_existing(local_mathlore, temp_dir)
            else:
                repo_url = f"https://github.com/{repo}.git"
                if self.github_client.token:
                    repo_url = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
                workspace = GitWorkspace.clone(repo_url, temp_dir)

            workspace.checkout_branch(branch_name, create=True)

            # Initialize Mathlingua agent to implement the plan
            agent = create_mathlingua_agent(
                content_root=workspace.workspace_dir,
                skills_dir=self.config.resolve_skills_dir(),
                mlg_bin=self.config.resolve_mlg_bin(),
                model=self.config.models.author,
                hooks=telemetry_hooks.get_hooks(),
                config=self.config,
            )

            execution_prompt = (
                f"You are executing an approved architectural plan for Mathlore.\n\n"
                f"### Issue #{issue_number}: {issue_record.title}\n\n"
                f"### Approved Plan (Revision {issue_record.plan_revision}):\n"
                f"{issue_record.plan_markdown}\n\n"
                f"### Instructions:\n"
                f"1. Create any necessary directories, `_preface_.mlg`, and `toc` files as specified in the plan.\n"
                f"2. Formulate and author the proposed mathematical items (Definitions, Theorems, Axioms, Proofs).\n"
                f"3. Run `mlg_check` to ensure zero diagnostics and generate UUIDs for all new items.\n"
                f"4. Run `mlg_format` to format according to configured margins.\n"
                f"5. Provide a summary of the files and items created."
            )

            async with agent:
                response = await agent.chat(execution_prompt)
                response_text = await response.text()
                run_record.conversation_id = agent.conversation_id

                if hasattr(agent, "conversation") and hasattr(agent.conversation, "total_usage"):
                    usage = agent.conversation.total_usage
                    run_record.prompt_tokens = getattr(usage, "prompt_token_count", 0)
                    run_record.candidates_tokens = getattr(usage, "candidates_token_count", 0)
                    run_record.thoughts_tokens = getattr(usage, "thoughts_token_count", 0)
                    run_record.total_tokens = getattr(usage, "total_token_count", 0)

            run_record.summary = response_text
            diff_patch = workspace.get_diff()
            run_record.diff_patch = diff_patch

            # Commit and push
            if workspace.has_changes():
                commit_msg = f"[Forge] Implement approved plan for #{issue_number}: {issue_record.title}"
                workspace.commit(commit_msg)

            try:
                if self.github_client.token:
                    auth_origin = f"https://x-access-token:{self.github_client.token}@github.com/{repo}.git"
                    workspace.run_git(["remote", "set-url", "origin", auth_origin], check=False)
                workspace.push("origin", branch_name)
            except Exception:
                pass

            # Open Pull Request
            pr_title = f"[Forge] {issue_record.title} (closes #{issue_number})"
            pr_body = (
                f"### Autonomous Mathlore Plan Implementation\n\n"
                f"Implements the approved curation plan for #{issue_number}.\n\n"
                f"#### Summary of Changes\n"
                f"{response_text}\n\n"
                f"---\n"
                f"*Authored by Mathlore Forge Curator & Mathlingua Engine.*"
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
                issue_record.status = "AWAITING_PR_REVIEW"

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

                # Comment on issue linking to PR
                await self.github_client.create_issue_comment(
                    repo=repo,
                    issue_or_pr_number=issue_number,
                    body=(
                        f"@{issue_record.author} The approved plan has been implemented and submitted in PR #{pr.number} ({pr.html_url})!\n\n"
                        f"- **Live Agent Run**: [View Run on Mathlore Forge Dashboard]({dash_link})\n\n"
                        f"Please review the pull request changes. You can comment `/forge accept` on the PR to validate and merge."
                    ),
                )
                try:
                    await self.github_client.create_issue_comment(
                        repo=repo,
                        issue_or_pr_number=pr.number,
                        body=(
                            f"@{issue_record.author} The approved curation plan for issue #{issue_number} has been implemented.\n\n"
                            f"- To request modifications: comment `/forge address`\n"
                            f"- To accept and merge: comment `/forge accept` (I will validate via `mlg check`, resolve any compiler issues, wait for CI checks, and merge into `main`)"
                        ),
                    )
                except Exception:
                    pass
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
