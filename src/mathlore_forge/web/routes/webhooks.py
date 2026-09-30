"""GitHub Webhook endpoint handler."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from mathlore_forge.config import ensure_env_loaded
from mathlore_forge.storage.db import IssueRecord, get_db, init_db
from mathlore_forge.workflows.authoring_flow import AuthoringFlow
from mathlore_forge.workflows.curation_flow import CurationFlow
from mathlore_forge.workflows.flywheel_flow import FlywheelFlow
from mathlore_forge.workflows.github_client import GitHubClient, GitHubIssue
from mathlore_forge.workflows.intent import IssueIntent, classify_issue_intent
from mathlore_forge.workflows.review_flow import ReviewFlow

ensure_env_loaded()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

ALLOWED_AUTHOR = os.getenv("ALLOWED_GITHUB_AUTHOR", "DominicKramer").strip().lower()
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
FORGE_LABEL = os.getenv("FORGE_ISSUE_LABEL", "forge").strip().lower()


def is_authorized_user(username: str | None) -> bool:
    """Verifies that the GitHub username matches Dominic Kramer."""
    if not username:
        return False
    return username.lower() == ALLOWED_AUTHOR or username.lower() == "dominickramer"


def has_forge_marker(issue_data: dict[str, Any]) -> bool:
    """Checks whether the issue has the forge label or title marker."""
    title = issue_data.get("title", "").lower()
    if "[forge]" in title:
        return True

    labels = issue_data.get("labels", [])
    for label in labels:
        name = label.get("name", "").lower() if isinstance(label, dict) else str(label).lower()
        if name in (FORGE_LABEL, "forge-task", "mathlore-forge"):
            return True

    return False


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Receives and processes GitHub Webhook events."""
    body_bytes = await request.body()

    # 1. Verify HMAC signature if secret configured
    if WEBHOOK_SECRET:
        valid = GitHubClient.verify_webhook_signature(body_bytes, x_hub_signature_256, WEBHOOK_SECRET)
        if not valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = x_github_event or request.headers.get("x-github-event")

    sender = payload.get("sender", {}).get("login", "")
    repo_full_name = payload.get("repository", {}).get("full_name", "mathlingua/mathlore")

    # 2. Handle Issues Event (Initial Trigger: Planning vs Direct Authoring)
    if event_type == "issues":
        action = payload.get("action")
        issue = payload.get("issue", {})
        issue_number = issue.get("number")
        author = issue.get("user", {}).get("login", "")

        # Only process if action is opened or labeled, and author/sender is authorized
        if action in ("opened", "labeled"):
            if is_authorized_user(author) or is_authorized_user(sender):
                if has_forge_marker(issue):
                    title = issue.get("title", "")
                    body = issue.get("body", "") or ""
                    labels = [
                        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
                        for lbl in issue.get("labels", [])
                    ]
                    intent = classify_issue_intent(title=title, body=body, labels=labels)

                    if intent == IssueIntent.HIGHER_ORDER_PLANNING:
                        asyncio.create_task(
                            _run_curation_planning_task(repo_full_name, issue_number, issue_data=issue)
                        )
                        return {
                            "status": "accepted",
                            "workflow": "curation_planning",
                            "repo": repo_full_name,
                            "issue": issue_number,
                        }
                    else:
                        asyncio.create_task(
                            _run_authoring_task(repo_full_name, issue_number, issue_data=issue)
                        )
                        return {
                            "status": "accepted",
                            "workflow": "authoring",
                            "repo": repo_full_name,
                            "issue": issue_number,
                        }

    # 3. Handle Pull Request Review Event (Approval / Changes Requested)
    elif event_type == "pull_request_review":
        action = payload.get("action")
        pr = payload.get("pull_request", {})
        review = payload.get("review", {})
        review_state = review.get("state", "").lower()  # approved, changes_requested, commented
        pr_number = pr.get("number")
        review_author = review.get("user", {}).get("login", "")

        if action == "submitted" and is_authorized_user(review_author):
            if review_state == "approved":
                # Step 8 & 9: Trigger Flywheel and Merge
                asyncio.create_task(
                    _run_flywheel_task(repo_full_name, pr_number)
                )
                return {
                    "status": "accepted",
                    "workflow": "flywheel_and_merge",
                    "repo": repo_full_name,
                    "pr": pr_number,
                }
            elif review_state in ("changes_requested", "commented"):
                # Step 5: Address Comments
                asyncio.create_task(
                    _run_review_task(repo_full_name, pr_number)
                )
                return {
                    "status": "accepted",
                    "workflow": "address_review_comments",
                    "repo": repo_full_name,
                    "pr": pr_number,
                }

    # 4. Handle Issue/PR Comments (Slash Commands & Interactive Proposal Refinement)
    elif event_type == "issue_comment":
        action = payload.get("action")
        comment = payload.get("comment", {})
        comment_body = comment.get("body", "").lower().strip()
        comment_author = comment.get("user", {}).get("login", "")
        issue = payload.get("issue", {})
        issue_or_pr_number = issue.get("number")
        is_pr = "pull_request" in issue

        if action == "created" and is_authorized_user(comment_author):
            if is_pr:
                if "/forge address" in comment_body or "@mathlore-forge address" in comment_body:
                    asyncio.create_task(
                        _run_review_task(repo_full_name, issue_or_pr_number)
                    )
                    return {
                        "status": "accepted",
                        "workflow": "address_review_comments",
                        "pr": issue_or_pr_number,
                    }
                elif "/forge approve" in comment_body or "/forge merge" in comment_body:
                    asyncio.create_task(
                        _run_flywheel_task(repo_full_name, issue_or_pr_number)
                    )
                    return {
                        "status": "accepted",
                        "workflow": "flywheel_and_merge",
                        "pr": issue_or_pr_number,
                    }
            else:
                # Dominic interacting with an Issue (Planning, Refinement, Execution)
                if any(cmd in comment_body for cmd in ("/forge execute", "/forge approve-plan", "/forge approve", "@mathlore-forge execute", "@mathlore-forge approve")):
                    asyncio.create_task(
                        _run_curation_execution_task(repo_full_name, issue_or_pr_number)
                    )
                    return {
                        "status": "accepted",
                        "workflow": "curation_plan_execution",
                        "repo": repo_full_name,
                        "issue": issue_or_pr_number,
                    }
                elif "/forge plan" in comment_body or "@mathlore-forge plan" in comment_body:
                    asyncio.create_task(
                        _run_curation_planning_task(repo_full_name, issue_or_pr_number, issue_data=issue)
                    )
                    return {
                        "status": "accepted",
                        "workflow": "curation_planning",
                        "repo": repo_full_name,
                        "issue": issue_or_pr_number,
                    }
                else:
                    # Check if this issue is tracked and has an active plan to refine
                    db_mgr = init_db()
                    has_active_plan = False
                    with db_mgr.get_session() as session:
                        rec = (
                            session.query(IssueRecord)
                            .filter_by(repo=repo_full_name, issue_number=issue_or_pr_number)
                            .first()
                        )
                        if rec and (rec.plan_markdown or rec.plan_status in ("PLANNING", "AWAITING_APPROVAL")):
                            has_active_plan = True

                    if has_active_plan:
                        raw_feedback = comment.get("body", "")
                        asyncio.create_task(
                            _run_curation_refinement_task(
                                repo_full_name, issue_or_pr_number, feedback=raw_feedback
                            )
                        )
                        return {
                            "status": "accepted",
                            "workflow": "curation_plan_refinement",
                            "repo": repo_full_name,
                            "issue": issue_or_pr_number,
                        }

    return {"status": "ignored", "event": event_type}


async def _run_authoring_task(repo: str, issue_number: int, issue_data: dict[str, Any] | None = None) -> None:
    """Background execution runner for authoring flow."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = AuthoringFlow()
        initial_issue = None
        if issue_data and issue_data.get("title"):
            labels = []
            for item in issue_data.get("labels", []):
                if isinstance(item, dict):
                    labels.append(item.get("name", ""))
                elif isinstance(item, str):
                    labels.append(item)
            initial_issue = GitHubIssue(
                number=issue_number,
                title=issue_data.get("title", ""),
                body=issue_data.get("body", "") or "",
                author=issue_data.get("user", {}).get("login", "") or issue_data.get("author", ""),
                labels=labels,
                state=issue_data.get("state", "open"),
                html_url=issue_data.get("html_url", ""),
            )
        try:
            await flow.execute(
                repo=repo,
                issue_number=issue_number,
                db_session=session,
                initial_issue=initial_issue,
            )
        except Exception as e:
            logger.error("Authoring flow failed for %s#%s: %s", repo, issue_number, e, exc_info=True)


async def _run_curation_planning_task(
    repo: str, issue_number: int, issue_data: dict[str, Any] | None = None
) -> None:
    """Background execution runner for curation and architectural planning flow."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = CurationFlow()
        title = ""
        body = ""
        author = "DominicKramer"
        if issue_data and issue_data.get("title"):
            title = issue_data.get("title", "")
            body = issue_data.get("body", "") or ""
            author = issue_data.get("user", {}).get("login", "") or issue_data.get("author", "DominicKramer")
        else:
            issue = await flow.github_client.get_issue(repo, issue_number)
            title = issue.title
            body = issue.body
            author = issue.author

        try:
            await flow.handle_initial_proposal(
                repo=repo,
                issue_number=issue_number,
                issue_title=title,
                issue_body=body,
                author=author,
                db_session=session,
            )
        except Exception as e:
            logger.error("Curation planning failed for %s#%s: %s", repo, issue_number, e, exc_info=True)


async def _run_curation_refinement_task(
    repo: str, issue_number: int, feedback: str
) -> None:
    """Background execution runner for proposal refinement based on Dominic Kramer's feedback."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = CurationFlow()
        try:
            await flow.handle_proposal_refinement(
                repo=repo,
                issue_number=issue_number,
                user_feedback=feedback,
                db_session=session,
            )
        except Exception as e:
            logger.error("Curation refinement failed for %s#%s: %s", repo, issue_number, e, exc_info=True)


async def _run_curation_execution_task(repo: str, issue_number: int) -> None:
    """Background execution runner for executing an approved plan."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = CurationFlow()
        try:
            await flow.handle_plan_execution(
                repo=repo,
                issue_number=issue_number,
                db_session=session,
            )
        except Exception as e:
            logger.error("Plan execution failed for %s#%s: %s", repo, issue_number, e, exc_info=True)


async def _run_review_task(repo: str, pr_number: int) -> None:
    """Background execution runner for review comment resolution."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = ReviewFlow()
        try:
            await flow.execute(repo=repo, pr_number=pr_number, db_session=session)
        except Exception as e:
            logger.error("Review resolution flow failed for %s#%s: %s", repo, pr_number, e, exc_info=True)


async def _run_flywheel_task(repo: str, pr_number: int) -> None:
    """Background execution runner for flywheel and PR merging."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = FlywheelFlow()
        try:
            await flow.execute(mathlore_repo=repo, pr_number=pr_number, db_session=session)
        except Exception as e:
            logger.error("Flywheel flow failed for %s#%s: %s", repo, pr_number, e, exc_info=True)
