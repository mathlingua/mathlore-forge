"""REST API and SSE streaming endpoints for agent monitoring and control."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from mathlore_forge.config import load_config
from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    RunType,
    TrajectoryRecord,
    get_db,
)
from mathlore_forge.web.auth import require_admin_user
from mathlore_forge.workflows.authoring_flow import AuthoringFlow

router = APIRouter(prefix="/api", tags=["API"])

# In-memory registry of active run cancellation events & event channels
_ACTIVE_CANCEL_FLAGS: dict[str, asyncio.Event] = {}
_ACTIVE_EVENT_QUEUES: dict[str, list[asyncio.Queue]] = {}


def register_event_queue(run_id: str, queue: asyncio.Queue) -> None:
    if run_id not in _ACTIVE_EVENT_QUEUES:
        _ACTIVE_EVENT_QUEUES[run_id] = []
    _ACTIVE_EVENT_QUEUES[run_id].append(queue)


def unregister_event_queue(run_id: str, queue: asyncio.Queue) -> None:
    if run_id in _ACTIVE_EVENT_QUEUES:
        if queue in _ACTIVE_EVENT_QUEUES[run_id]:
            _ACTIVE_EVENT_QUEUES[run_id].remove(queue)


def broadcast_run_event(run_id: str, event_data: dict[str, Any]) -> None:
    """Broadcasts a live telemetry event to all connected SSE clients."""
    queues = _ACTIVE_EVENT_QUEUES.get(run_id, [])
    for q in queues:
        try:
            q.put_nowait(event_data)
        except Exception:
            pass


class ManualRunRequest(BaseModel):
    repo: str = "mathlingua/mathlore"
    issue_number: int | None = None
    custom_prompt: str | None = None


@router.get("/runs")
def list_runs(
    limit: int = 50,
    status_filter: RunStatus | None = None,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> list[dict[str, Any]]:
    """Lists agent runs, newest first."""
    query = db.query(AgentRunRecord)
    if status_filter:
        query = query.filter(AgentRunRecord.status == status_filter)
    runs = query.order_by(desc(AgentRunRecord.started_at)).limit(limit).all()

    return [
        {
            "id": r.id,
            "run_type": r.run_type.value,
            "status": r.status.value,
            "repo": r.repo,
            "issue_number": r.issue_number,
            "pr_number": r.pr_number,
            "branch_name": r.branch_name,
            "duration_seconds": round(r.duration_seconds, 2),
            "total_tokens": r.total_tokens,
            "thoughts_tokens": r.thoughts_tokens,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Retrieves full details for a specific run."""
    run = db.query(AgentRunRecord).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    traj = db.query(TrajectoryRecord).filter_by(run_id=run_id).first()
    return {
        "id": run.id,
        "run_type": run.run_type.value,
        "status": run.status.value,
        "repo": run.repo,
        "issue_number": run.issue_number,
        "pr_number": run.pr_number,
        "branch_name": run.branch_name,
        "prompt": run.prompt,
        "summary": run.summary,
        "error_message": run.error_message,
        "diff_patch": run.diff_patch,
        "tokens": {
            "prompt": run.prompt_tokens,
            "candidates": run.candidates_tokens,
            "thoughts": run.thoughts_tokens,
            "total": run.total_tokens,
        },
        "duration_seconds": round(run.duration_seconds, 2),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "has_trajectory": traj is not None,
    }


@router.get("/runs/{run_id}/trajectory")
def get_run_trajectory(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Retrieves full parsed trajectory JSON for deep inspection."""
    traj = db.query(TrajectoryRecord).filter_by(run_id=run_id).first()
    if not traj or not traj.trajectory_json:
        raise HTTPException(status_code=404, detail=f"Trajectory for run '{run_id}' not found")
    try:
        return json.loads(traj.trajectory_json)
    except Exception:
        return {"raw": traj.trajectory_json}


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, str]:
    """Cancels a currently active agent run."""
    run = db.query(AgentRunRecord).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status in (RunStatus.RUNNING, RunStatus.QUEUED):
        run.status = RunStatus.CANCELLED
        run.error_message = "Cancelled by Dominic Kramer via dashboard."
        db.commit()

        # Signal cancellation event
        if run_id in _ACTIVE_CANCEL_FLAGS:
            _ACTIVE_CANCEL_FLAGS[run_id].set()

        broadcast_run_event(run_id, {"event": "cancelled", "message": "Run cancelled."})
        return {"status": "success", "message": f"Run {run_id} marked as CANCELLED."}

    return {"status": "ignored", "message": f"Run is already in status {run.status.value}."}


@router.post("/runs/{run_id}/restart")
async def restart_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, str]:
    """Restarts an agent run."""
    run = db.query(AgentRunRecord).filter_by(id=run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.issue_number:
        flow = AuthoringFlow()
        asyncio.create_task(flow.execute(repo=run.repo, issue_number=run.issue_number, db_session=db))
        return {"status": "success", "message": f"Restarted authoring run for issue #{run.issue_number}"}

    raise HTTPException(status_code=400, detail="Cannot restart run without issue_number")


@router.post("/runs/manual")
async def trigger_manual_run(
    payload: ManualRunRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Manually triggers an agent authoring run."""
    if not payload.issue_number:
        raise HTTPException(status_code=400, detail="issue_number is required for authoring run")

    flow = AuthoringFlow()
    asyncio.create_task(flow.execute(repo=payload.repo, issue_number=payload.issue_number, db_session=db))
    return {
        "status": "queued",
        "repo": payload.repo,
        "issue_number": payload.issue_number,
        "message": "Manual authoring run queued successfully.",
    }


@router.get("/runs/{run_id}/stream")
async def stream_run_trajectory(
    run_id: str,
    request: Request,
    user: dict[str, Any] = Depends(require_admin_user),
) -> StreamingResponse:
    """Server-Sent Events (SSE) live streaming endpoint for agent trajectory & thoughts."""

    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        register_event_queue(run_id, queue)
        try:
            # Send initial connection ping
            yield f"event: ping\ndata: {json.dumps({'status': 'connected', 'run_id': run_id})}\n\n"

            while True:
                # Disconnect check
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: update\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat
                    yield f"event: heartbeat\ndata: {json.dumps({'time': datetime.now(timezone.utc).isoformat()})}\n\n"
        finally:
            unregister_event_queue(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/flywheel/guidelines")
def get_learned_guidelines(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Returns learned guidelines from skills/mathlore-learned-guidelines/SKILL.md."""
    config = load_config()
    skills_dir = config.resolve_skills_dir()
    skill_file = Path(skills_dir) / "mathlore-learned-guidelines" / "SKILL.md"

    content = ""
    if skill_file.is_file():
        content = skill_file.read_text(encoding="utf-8")

    return {
        "path": str(skill_file),
        "content": content,
    }
