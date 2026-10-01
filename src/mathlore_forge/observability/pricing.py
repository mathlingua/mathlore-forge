"""Cost and duration analytics calculator for Mathlore Forge agent runs."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, Sequence
from sqlalchemy.orm import Session

from mathlore_forge.storage.db import (
    AgentRunRecord,
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    RunType,
)

# Standard pricing rates per 1,000,000 tokens (USD)
# Can be overridden via environment variables
DEFAULT_FLASH_INPUT_RATE = float(os.getenv("PRICING_FLASH_INPUT_PER_M", "0.10"))
DEFAULT_FLASH_OUTPUT_RATE = float(os.getenv("PRICING_FLASH_OUTPUT_PER_M", "0.40"))
DEFAULT_PRO_INPUT_RATE = float(os.getenv("PRICING_PRO_INPUT_PER_M", "1.25"))
DEFAULT_PRO_OUTPUT_RATE = float(os.getenv("PRICING_PRO_OUTPUT_PER_M", "5.00"))

MODEL_PRICING: dict[str, dict[str, Any]] = {
    "gemini-3.8-flash": {
        "display_name": "Gemini 3.8 Flash",
        "input_rate_per_m": DEFAULT_FLASH_INPUT_RATE,
        "output_rate_per_m": DEFAULT_FLASH_OUTPUT_RATE,
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "input_rate_per_m": DEFAULT_FLASH_INPUT_RATE,
        "output_rate_per_m": DEFAULT_FLASH_OUTPUT_RATE,
    },
    "gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
        "input_rate_per_m": DEFAULT_FLASH_INPUT_RATE,
        "output_rate_per_m": DEFAULT_FLASH_OUTPUT_RATE,
    },
    "gemini-1.5-flash": {
        "display_name": "Gemini 1.5 Flash",
        "input_rate_per_m": DEFAULT_FLASH_INPUT_RATE,
        "output_rate_per_m": DEFAULT_FLASH_OUTPUT_RATE,
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "input_rate_per_m": DEFAULT_PRO_INPUT_RATE,
        "output_rate_per_m": DEFAULT_PRO_OUTPUT_RATE,
    },
    "gemini-1.5-pro": {
        "display_name": "Gemini 1.5 Pro",
        "input_rate_per_m": DEFAULT_PRO_INPUT_RATE,
        "output_rate_per_m": DEFAULT_PRO_OUTPUT_RATE,
    },
    "default": {
        "display_name": "Gemini Standard",
        "input_rate_per_m": DEFAULT_FLASH_INPUT_RATE,
        "output_rate_per_m": DEFAULT_FLASH_OUTPUT_RATE,
    },
}


def get_model_pricing(model_name: str | None) -> dict[str, Any]:
    """Resolves model pricing details, matching prefixes and aliases."""
    if not model_name:
        return MODEL_PRICING["default"]
    lower = model_name.lower().strip()
    for key, val in MODEL_PRICING.items():
        if key in lower:
            return val
    if "pro" in lower:
        return MODEL_PRICING["gemini-2.5-pro"]
    return MODEL_PRICING["default"]


def format_duration(seconds: float | None) -> str:
    """Formats a duration in seconds into a clean human-readable string."""
    if seconds is None or seconds <= 0:
        return "0s"
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins < 60:
        return f"{mins}m {secs:02d}s"
    hours = mins // 60
    rem_mins = mins % 60
    return f"{hours}h {rem_mins:02d}m"


def format_cost(cost: float) -> str:
    """Formats a cost in USD to appropriate decimal precision."""
    if cost <= 0:
        return "$0.00"
    if cost < 0.001:
        return f"${cost:.5f}"
    if cost < 0.01:
        return f"${cost:.4f}"
    return f"${cost:.3f}"


def calculate_run_cost(
    model_name: str | None,
    prompt_tokens: int,
    candidates_tokens: int,
    thoughts_tokens: int = 0,
    total_tokens: int = 0,
) -> dict[str, Any]:
    """Calculates granular pricing for an agent run based on token metrics."""
    pricing = get_model_pricing(model_name)
    input_rate = pricing["input_rate_per_m"]
    output_rate = pricing["output_rate_per_m"]

    eff_input = max(0, prompt_tokens)
    eff_output = max(0, candidates_tokens)
    if eff_output == 0 and total_tokens > eff_input:
        eff_output = total_tokens - eff_input

    input_cost = (eff_input / 1_000_000.0) * input_rate
    output_cost = (eff_output / 1_000_000.0) * output_rate
    total_cost = input_cost + output_cost

    return {
        "model_name": model_name or "gemini-3.8-flash",
        "display_name": pricing["display_name"],
        "input_tokens": eff_input,
        "output_tokens": eff_output,
        "thoughts_tokens": thoughts_tokens,
        "total_tokens": total_tokens or (eff_input + eff_output),
        "input_rate_per_m": input_rate,
        "output_rate_per_m": output_rate,
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total_cost, 5),
        "formatted_input_cost": format_cost(input_cost),
        "formatted_output_cost": format_cost(output_cost),
        "formatted_total_cost": format_cost(total_cost),
    }


def aggregate_issue_analytics(session: Session) -> dict[str, Any]:
    """Aggregates all tracked issues and agent runs into per-issue and global cost/time analytics."""
    issues = session.query(IssueRecord).order_by(IssueRecord.issue_number.desc()).all()
    all_runs = session.query(AgentRunRecord).order_by(AgentRunRecord.started_at.asc()).all()
    all_prs = session.query(PullRequestRecord).all()

    # Map PRs to issue IDs
    pr_to_issue: dict[int, int] = {}
    for pr in all_prs:
        if pr.issue_id:
            pr_to_issue[pr.pr_number] = pr.issue_id

    # Group runs by issue
    issue_runs: dict[int, list[AgentRunRecord]] = {issue.id: [] for issue in issues}
    unassociated_runs: list[AgentRunRecord] = []

    for run in all_runs:
        matched_issue_id = None
        if run.issue_id and run.issue_id in issue_runs:
            matched_issue_id = run.issue_id
        elif run.issue_number:
            for iss in issues:
                if iss.repo == run.repo and iss.issue_number == run.issue_number:
                    matched_issue_id = iss.id
                    break
        if not matched_issue_id and run.pr_number and run.pr_number in pr_to_issue:
            matched_issue_id = pr_to_issue[run.pr_number]

        if matched_issue_id and matched_issue_id in issue_runs:
            issue_runs[matched_issue_id].append(run)
        else:
            unassociated_runs.append(run)

    # Global aggregators
    global_total_cost = 0.0
    global_total_duration = 0.0
    global_input_tokens = 0
    global_output_tokens = 0
    global_thoughts_tokens = 0
    global_total_tokens = 0

    phase_totals: dict[str, dict[str, Any]] = {
        "planning": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0, "label": "Curation Planning"},
        "authoring": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0, "label": "Authoring & Execution"},
        "review": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0, "label": "Review Resolution"},
        "flywheel": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0, "label": "Flywheel Self-Improvement"},
    }

    model_totals: dict[str, dict[str, Any]] = {}

    def categorize_phase(run_type: RunType) -> str:
        if run_type in (RunType.CURATION_PLANNING,):
            return "planning"
        if run_type in (RunType.INITIAL_AUTHORING, RunType.PLAN_EXECUTION):
            return "authoring"
        if run_type in (RunType.ADDRESS_COMMENTS,):
            return "review"
        if run_type in (RunType.FLYWHEEL_IMPROVEMENT,):
            return "flywheel"
        return "authoring"

    analyzed_issues: list[dict[str, Any]] = []

    for issue in issues:
        runs = issue_runs[issue.id]
        issue_cost = 0.0
        issue_duration = 0.0
        issue_input_tokens = 0
        issue_output_tokens = 0
        issue_thoughts_tokens = 0
        issue_total_tokens = 0

        issue_phase_breakdown: dict[str, dict[str, Any]] = {
            "planning": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0},
            "authoring": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0},
            "review": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0},
            "flywheel": {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0},
        }

        run_details: list[dict[str, Any]] = []

        for r in runs:
            cost_info = calculate_run_cost(
                model_name=r.model_name,
                prompt_tokens=r.prompt_tokens,
                candidates_tokens=r.candidates_tokens,
                thoughts_tokens=r.thoughts_tokens,
                total_tokens=r.total_tokens,
            )
            r_cost = cost_info["total_cost"]
            r_dur = r.duration_seconds or 0.0
            r_tokens = cost_info["total_tokens"]

            issue_cost += r_cost
            issue_duration += r_dur
            issue_input_tokens += cost_info["input_tokens"]
            issue_output_tokens += cost_info["output_tokens"]
            issue_thoughts_tokens += cost_info["thoughts_tokens"]
            issue_total_tokens += r_tokens

            phase = categorize_phase(r.run_type)
            issue_phase_breakdown[phase]["cost"] += r_cost
            issue_phase_breakdown[phase]["duration"] += r_dur
            issue_phase_breakdown[phase]["tokens"] += r_tokens
            issue_phase_breakdown[phase]["runs"] += 1

            phase_totals[phase]["cost"] += r_cost
            phase_totals[phase]["duration"] += r_dur
            phase_totals[phase]["tokens"] += r_tokens
            phase_totals[phase]["runs"] += 1

            # Model breakdown
            m_name = cost_info["display_name"]
            if m_name not in model_totals:
                model_totals[m_name] = {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0}
            model_totals[m_name]["cost"] += r_cost
            model_totals[m_name]["duration"] += r_dur
            model_totals[m_name]["tokens"] += r_tokens
            model_totals[m_name]["runs"] += 1

            run_details.append({
                "id": r.id,
                "run_type": r.run_type.value,
                "phase_category": phase,
                "status": r.status.value,
                "model_name": cost_info["display_name"],
                "raw_model": r.model_name or "gemini-3.8-flash",
                "duration_seconds": round(r_dur, 2),
                "formatted_duration": format_duration(r_dur),
                "started_at": r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else None,
                "completed_at": r.completed_at.strftime("%Y-%m-%d %H:%M:%S") if r.completed_at else None,
                "cost": cost_info,
                "summary": r.summary or "",
                "pr_number": r.pr_number,
                "branch_name": r.branch_name,
            })

        global_total_cost += issue_cost
        global_total_duration += issue_duration
        global_input_tokens += issue_input_tokens
        global_output_tokens += issue_output_tokens
        global_thoughts_tokens += issue_thoughts_tokens
        global_total_tokens += issue_total_tokens

        # Format phase breakdowns
        for p in issue_phase_breakdown.values():
            p["formatted_cost"] = format_cost(p["cost"])
            p["formatted_duration"] = format_duration(p["duration"])

        analyzed_issues.append({
            "id": issue.id,
            "issue_number": issue.issue_number,
            "repo": issue.repo,
            "title": issue.title,
            "author": issue.author,
            "status": issue.status,
            "plan_status": issue.plan_status,
            "plan_revision": issue.plan_revision,
            "created_at": issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else None,
            "total_runs": len(runs),
            "total_cost": round(issue_cost, 5),
            "formatted_total_cost": format_cost(issue_cost),
            "total_duration_seconds": round(issue_duration, 2),
            "formatted_total_duration": format_duration(issue_duration),
            "input_tokens": issue_input_tokens,
            "output_tokens": issue_output_tokens,
            "thoughts_tokens": issue_thoughts_tokens,
            "total_tokens": issue_total_tokens,
            "phase_breakdown": issue_phase_breakdown,
            "runs": run_details,
        })

    # Include unassociated runs in global analytics
    unassociated_details: list[dict[str, Any]] = []
    unassociated_cost = 0.0
    unassociated_duration = 0.0
    for r in unassociated_runs:
        cost_info = calculate_run_cost(
            model_name=r.model_name,
            prompt_tokens=r.prompt_tokens,
            candidates_tokens=r.candidates_tokens,
            thoughts_tokens=r.thoughts_tokens,
            total_tokens=r.total_tokens,
        )
        r_cost = cost_info["total_cost"]
        r_dur = r.duration_seconds or 0.0
        unassociated_cost += r_cost
        unassociated_duration += r_dur
        global_total_cost += r_cost
        global_total_duration += r_dur
        global_total_tokens += cost_info["total_tokens"]
        global_input_tokens += cost_info["input_tokens"]
        global_output_tokens += cost_info["output_tokens"]
        global_thoughts_tokens += cost_info["thoughts_tokens"]

        phase = categorize_phase(r.run_type)
        phase_totals[phase]["cost"] += r_cost
        phase_totals[phase]["duration"] += r_dur
        phase_totals[phase]["tokens"] += cost_info["total_tokens"]
        phase_totals[phase]["runs"] += 1

        m_name = cost_info["display_name"]
        if m_name not in model_totals:
            model_totals[m_name] = {"cost": 0.0, "duration": 0.0, "tokens": 0, "runs": 0}
        model_totals[m_name]["cost"] += r_cost
        model_totals[m_name]["duration"] += r_dur
        model_totals[m_name]["tokens"] += cost_info["total_tokens"]
        model_totals[m_name]["runs"] += 1

        unassociated_details.append({
            "id": r.id,
            "run_type": r.run_type.value,
            "phase_category": phase,
            "status": r.status.value,
            "model_name": cost_info["display_name"],
            "raw_model": r.model_name or "gemini-3.8-flash",
            "duration_seconds": round(r_dur, 2),
            "formatted_duration": format_duration(r_dur),
            "started_at": r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else None,
            "completed_at": r.completed_at.strftime("%Y-%m-%d %H:%M:%S") if r.completed_at else None,
            "cost": cost_info,
            "summary": r.summary or "",
            "pr_number": r.pr_number,
            "branch_name": r.branch_name,
        })

    # Compute percentages and formatted strings for global phases
    for p_key, p_val in phase_totals.items():
        p_val["formatted_cost"] = format_cost(p_val["cost"])
        p_val["formatted_duration"] = format_duration(p_val["duration"])
        p_val["cost_percentage"] = round((p_val["cost"] / global_total_cost * 100), 1) if global_total_cost > 0 else 0.0
        p_val["time_percentage"] = round((p_val["duration"] / global_total_duration * 100), 1) if global_total_duration > 0 else 0.0

    for m_val in model_totals.values():
        m_val["formatted_cost"] = format_cost(m_val["cost"])
        m_val["formatted_duration"] = format_duration(m_val["duration"])

    avg_cost = (global_total_cost / len(issues)) if issues else 0.0
    avg_dur = (global_total_duration / len(issues)) if issues else 0.0

    return {
        "issues": analyzed_issues,
        "unassociated_runs": unassociated_details,
        "unassociated_cost": round(unassociated_cost, 5),
        "formatted_unassociated_cost": format_cost(unassociated_cost),
        "total_issues_count": len(issues),
        "global_total_cost": round(global_total_cost, 5),
        "formatted_global_total_cost": format_cost(global_total_cost),
        "global_total_duration": round(global_total_duration, 2),
        "formatted_global_total_duration": format_duration(global_total_duration),
        "average_cost_per_issue": round(avg_cost, 5),
        "formatted_average_cost_per_issue": format_cost(avg_cost),
        "average_duration_per_issue": round(avg_dur, 2),
        "formatted_average_duration_per_issue": format_duration(avg_dur),
        "global_total_tokens": global_total_tokens,
        "global_input_tokens": global_input_tokens,
        "global_output_tokens": global_output_tokens,
        "global_thoughts_tokens": global_thoughts_tokens,
        "phase_totals": phase_totals,
        "model_totals": model_totals,
    }
