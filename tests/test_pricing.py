"""Unit tests for cost and duration observability analytics."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from mathlore_forge.storage.db import (
    AgentRunRecord,
    Base,
    IssueRecord,
    PullRequestRecord,
    RunStatus,
    RunType,
    get_db,
    init_db,
)
from mathlore_forge.observability.pricing import (
    aggregate_issue_analytics,
    calculate_run_cost,
    format_cost,
    format_duration,
    get_model_pricing,
)
from mathlore_forge.web.app import create_app
from mathlore_forge.web.auth import create_session_token


def test_pricing_calculations() -> None:
    flash_pricing = get_model_pricing("gemini-3.8-flash")
    assert flash_pricing["input_rate_per_m"] == 0.10
    assert flash_pricing["output_rate_per_m"] == 0.40

    pro_pricing = get_model_pricing("gemini-2.5-pro")
    assert pro_pricing["input_rate_per_m"] == 1.25
    assert pro_pricing["output_rate_per_m"] == 5.00

    # 1M input tokens + 1M output tokens on Flash = $0.10 + $0.40 = $0.50
    cost_calc = calculate_run_cost(
        model_name="gemini-3.8-flash",
        prompt_tokens=1_000_000,
        candidates_tokens=1_000_000,
        thoughts_tokens=500_000,
        total_tokens=2_500_000,
    )
    assert cost_calc["input_cost"] == pytest.approx(0.10, rel=1e-3)
    assert cost_calc["output_cost"] == pytest.approx(0.40, rel=1e-3)
    assert cost_calc["total_cost"] == pytest.approx(0.50, rel=1e-3)
    assert cost_calc["formatted_total_cost"] == "$0.500"

    # Small token amount formatting
    small_calc = calculate_run_cost(
        model_name="gemini-3.8-flash",
        prompt_tokens=10_000,
        candidates_tokens=2_000,
    )
    assert small_calc["total_cost"] > 0
    assert "$" in small_calc["formatted_total_cost"]


def test_format_duration() -> None:
    assert format_duration(0) == "0s"
    assert format_duration(45.2) == "45.2s"
    assert format_duration(125.0) == "2m 05s"
    assert format_duration(3665.0) == "1h 01m"


def test_format_cost() -> None:
    assert format_cost(0.0) == "$0.00"
    assert format_cost(0.00045) == "$0.00045"
    assert format_cost(0.0085) == "$0.0085"
    assert format_cost(0.125) == "$0.125"


def test_aggregate_issue_analytics() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create issue #10
    issue10 = IssueRecord(
        issue_number=10,
        repo="mathlingua/mathlore",
        title="Normalize proof strings in Set Operations",
        author="DominicKramer",
        status="open",
        plan_status="APPROVED",
        plan_revision=1,
    )
    session.add(issue10)
    session.flush()

    # Run 1: Planning
    run_plan = AgentRunRecord(
        id="run_plan_10",
        repo="mathlingua/mathlore",
        run_type=RunType.CURATION_PLANNING,
        status=RunStatus.COMPLETED,
        issue_id=issue10.id,
        issue_number=10,
        model_name="gemini-3.8-flash",
        prompt="Draft proposal",
        prompt_tokens=50_000,
        candidates_tokens=10_000,
        thoughts_tokens=5_000,
        total_tokens=65_000,
        duration_seconds=30.0,
    )
    # Run 2: Authoring / Execution
    run_exec = AgentRunRecord(
        id="run_exec_10",
        repo="mathlingua/mathlore",
        run_type=RunType.PLAN_EXECUTION,
        status=RunStatus.AWAITING_REVIEW,
        issue_id=issue10.id,
        issue_number=10,
        pr_number=12,
        model_name="gemini-3.8-flash",
        prompt="Execute plan",
        prompt_tokens=80_000,
        candidates_tokens=15_000,
        thoughts_tokens=8_000,
        total_tokens=103_000,
        duration_seconds=45.0,
    )
    # Run 3: Standalone ad-hoc run
    run_standalone = AgentRunRecord(
        id="run_standalone_1",
        repo="mathlingua/mathlore",
        run_type=RunType.INITIAL_AUTHORING,
        status=RunStatus.COMPLETED,
        model_name="gemini-3.8-flash",
        prompt="Ad-hoc task",
        prompt_tokens=20_000,
        candidates_tokens=5_000,
        total_tokens=25_000,
        duration_seconds=15.0,
    )

    session.add_all([run_plan, run_exec, run_standalone])
    session.commit()

    analytics = aggregate_issue_analytics(session)

    assert analytics["total_issues_count"] == 1
    assert len(analytics["issues"]) == 1
    issue_data = analytics["issues"][0]
    assert issue_data["issue_number"] == 10
    assert issue_data["total_runs"] == 2
    assert issue_data["total_duration_seconds"] == 75.0
    assert issue_data["total_cost"] > 0
    assert issue_data["phase_breakdown"]["planning"]["runs"] == 1
    assert issue_data["phase_breakdown"]["authoring"]["runs"] == 1

    # Check unassociated runs
    assert len(analytics["unassociated_runs"]) == 1
    assert analytics["unassociated_runs"][0]["id"] == "run_standalone_1"

    # Check global totals include both issue runs and unassociated runs
    assert analytics["global_total_duration"] == 90.0
    assert analytics["global_total_tokens"] == (65_000 + 103_000 + 25_000)


def test_analytics_web_route() -> None:
    db_mgr = init_db("sqlite:///:memory:")
    with db_mgr.get_session() as session:
        issue = IssueRecord(
            issue_number=15,
            repo="mathlingua/mathlore",
            title="Define Commutativity of Disjoint Union",
            author="DominicKramer",
            status="open",
            plan_status="APPROVED",
        )
        session.add(issue)
        session.commit()

    app = create_app()
    client = TestClient(app)
    token = create_session_token("DominicKramer@gmail.com", "Dominic Kramer")
    client.cookies.set("forge_session", token)

    # HTML page
    resp = client.get("/analytics")
    assert resp.status_code == 200
    assert "Issue Cost & Duration Analytics" in resp.text
    assert "Define Commutativity of Disjoint Union" in resp.text

    # Alias /costs
    resp_alias = client.get("/costs")
    assert resp_alias.status_code == 200
    assert "Issue Cost & Duration Analytics" in resp_alias.text

    # JSON API endpoint
    api_resp = client.get("/api/analytics")
    assert api_resp.status_code == 200
    data = api_resp.json()
    assert "global_total_cost" in data
    assert "issues" in data
    assert len(data["issues"]) == 1
    assert data["issues"][0]["issue_number"] == 15
