"""GitHub Webhook endpoint handler."""

from __future__ import annotations

import asyncio
import os
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from mathlore_forge.storage.db import get_db, init_db
from mathlore_forge.workflows.authoring_flow import AuthoringFlow
from mathlore_forge.workflows.flywheel_flow import FlywheelFlow
from mathlore_forge.workflows.github_client import GitHubClient
from mathlore_forge.workflows.review_flow import ReviewFlow

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

    # 2. Handle Issues Event (Initial Authoring Trigger)
    if event_type == "issues":
        action = payload.get("action")
        issue = payload.get("issue", {})
        issue_number = issue.get("number")
        author = issue.get("user", {}).get("login", "")

        # Only process if action is opened or labeled, and author/sender is authorized
        if action in ("opened", "labeled"):
            if is_authorized_user(author) or is_authorized_user(sender):
                if has_forge_marker(issue):
                    authoring_flow = AuthoringFlow()
                    # Run background task
                    asyncio.create_task(
                        _run_authoring_task(repo_full_name, issue_number)
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

    # 4. Handle Issue/PR Comments (Slash Commands)
    elif event_type == "issue_comment":
        action = payload.get("action")
        comment = payload.get("comment", {})
        comment_body = comment.get("body", "").lower().strip()
        comment_author = comment.get("user", {}).get("login", "")
        issue = payload.get("issue", {})
        issue_or_pr_number = issue.get("number")
        is_pr = "pull_request" in issue

        if action == "created" and is_authorized_user(comment_author) and is_pr:
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

    return {"status": "ignored", "event": event_type}


async def _run_authoring_task(repo: str, issue_number: int) -> None:
    """Background execution runner for authoring flow."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = AuthoringFlow()
        await flow.execute(repo=repo, issue_number=issue_number, db_session=session)


async def _run_review_task(repo: str, pr_number: int) -> None:
    """Background execution runner for review comment resolution."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = ReviewFlow()
        await flow.execute(repo=repo, pr_number=pr_number, db_session=session)


async def _run_flywheel_task(repo: str, pr_number: int) -> None:
    """Background execution runner for flywheel and PR merging."""
    db_mgr = init_db()
    with db_mgr.get_session() as session:
        flow = FlywheelFlow()
        await flow.execute(mathlore_repo=repo, pr_number=pr_number, db_session=session)
