"""Dashboard HTML routes and Google OAuth endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from mathlore_forge.config import load_config
from mathlore_forge.goldens.loader import discover_test_cases
from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    TrajectoryRecord,
    get_db,
)
from mathlore_forge.web.auth import (
    ALLOWED_EMAIL,
    GOOGLE_CLIENT_ID,
    create_session_token,
    exchange_google_code,
    get_current_user,
    require_admin_user,
)

router = APIRouter(tags=["Dashboard"])

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None) -> Response:
    """Renders the Google Sign-In page."""
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None, "error": error},
    )


def _get_auth_redirect_uri(request: Request) -> str:
    """Build the OAuth redirect URI, ensuring HTTPS behind Cloud Run and reverse proxies."""
    url = request.url_for("auth_callback")
    proto = request.headers.get("x-forwarded-proto")
    if proto:
        url = url.replace(scheme=proto)
    elif "run.app" in request.url.netloc:
        url = url.replace(scheme="https")
    return str(url)


@router.get("/auth/google")
async def auth_google(request: Request) -> Response:
    """Redirects to Google OAuth authorization endpoint."""
    if not GOOGLE_CLIENT_ID:
        # Development mode fallback if OAuth credentials are not yet set
        if os.getenv("DEV_ALLOW_LOCAL_ADMIN") == "true":
            token = create_session_token(ALLOWED_EMAIL, "Dominic Kramer (Dev)")
            response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="forge_session",
                value=token,
                httponly=True,
                max_age=86400 * 7,
                samesite="lax",
            )
            return response
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    redirect_uri = _get_auth_redirect_uri(request)
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        "response_type=code&"
        "scope=openid%20email%20profile&"
        "access_type=offline&"
        "prompt=select_account"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request, code: str | None = None, error: str | None = None) -> Response:
    """Handles callback from Google OAuth and verifies email authorization."""
    if error or not code:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"user": None, "error": f"Google authentication failed: {error or 'No code'}"},
            status_code=400,
        )

    redirect_uri = _get_auth_redirect_uri(request)
    try:
        user_info = await exchange_google_code(code, redirect_uri)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"user": None, "error": exc.detail},
            status_code=exc.status_code,
        )

    # Email verified and authorized!
    token = create_session_token(user_info["email"], user_info.get("name", ""))
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="forge_session",
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax",
    )
    return response


@router.get("/auth/logout")
async def logout() -> Response:
    """Logs out and clears session cookie."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("forge_session")
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> Response:
    """Renders main dashboard page."""
    runs = db.query(AgentRunRecord).order_by(desc(AgentRunRecord.started_at)).limit(30).all()

    # Aggregate stats
    active_runs = db.query(func.count(AgentRunRecord.id)).filter(AgentRunRecord.status == RunStatus.RUNNING).scalar() or 0
    awaiting_review = db.query(func.count(AgentRunRecord.id)).filter(AgentRunRecord.status == RunStatus.AWAITING_REVIEW).scalar() or 0
    completed_runs = db.query(func.count(AgentRunRecord.id)).filter(AgentRunRecord.status == RunStatus.COMPLETED).scalar() or 0
    total_tokens = db.query(func.sum(AgentRunRecord.total_tokens)).scalar() or 0

    stats = {
        "active_runs": active_runs,
        "awaiting_review": awaiting_review,
        "completed_runs": completed_runs,
        "total_tokens": int(total_tokens),
    }

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "runs": runs,
            "stats": stats,
        },
    )


@router.get("/runs/{run_id}", response_class=HTMLResponse)
async def trajectory_page(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> Response:
    """Renders trajectory inspector page for an agent run."""
    run = db.query(AgentRunRecord).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    traj_rec = db.query(TrajectoryRecord).filter_by(run_id=run_id).first()
    trajectory_data = None
    if traj_rec and traj_rec.trajectory_json:
        try:
            trajectory_data = json.loads(traj_rec.trajectory_json)
        except Exception:
            pass

    return templates.TemplateResponse(
        request=request,
        name="trajectory.html",
        context={
            "user": user,
            "run": run,
            "trajectory": trajectory_data,
            "markdown_summary": traj_rec.markdown_summary if traj_rec else "",
        },
    )


@router.get("/flywheel", response_class=HTMLResponse)
async def flywheel_page(
    request: Request,
    user: dict[str, Any] = Depends(require_admin_user),
) -> Response:
    """Renders flywheel learned guidelines and golden tests explorer."""
    config = load_config()
    skills_dir = config.resolve_skills_dir()
    skill_file = Path(skills_dir) / "mathlore-learned-guidelines" / "SKILL.md"

    skill_content = ""
    if skill_file.is_file():
        skill_content = skill_file.read_text(encoding="utf-8")

    # Load golden tests
    goldens = []
    goldens_dir = Path(__file__).resolve().parent.parent.parent.parent / "golden_tests"
    if goldens_dir.is_dir():
        specs = discover_test_cases(goldens_dir)
        goldens = [{"id": s.id, "name": s.name, "description": s.description} for s in specs]

    return templates.TemplateResponse(
        request=request,
        name="flywheel.html",
        context={
            "user": user,
            "skill_content": skill_content,
            "goldens": goldens,
        },
    )
