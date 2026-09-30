"""Tests for REST API endpoints and agent controls."""

import pytest
from fastapi.testclient import TestClient

from mathlore_forge.storage.db import (
    AgentRunRecord,
    RunStatus,
    RunType,
    init_db,
)
from mathlore_forge.web.app import create_app
from mathlore_forge.web.auth import create_session_token


@pytest.fixture
def client():
    app = create_app()
    c = TestClient(app)
    # Authenticate as DominicKramer@gmail.com
    token = create_session_token("DominicKramer@gmail.com", "Dominic Kramer")
    c.cookies.set("forge_session", token)
    return c


def test_list_and_get_runs(client):
    db_mgr = init_db("sqlite:///:memory:")
    with db_mgr.get_session() as s:
        run = AgentRunRecord(
            id="run_api_test_1",
            run_type=RunType.INITIAL_AUTHORING,
            status=RunStatus.RUNNING,
            repo="mathlingua/mathlore",
            issue_number=88,
            prompt="Test prompt",
        )
        s.add(run)
        s.commit()

    resp = client.get("/api/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)

    resp_single = client.get(f"/api/runs/run_api_test_1")
    assert resp_single.status_code == 200
    data = resp_single.json()
    assert data["id"] == "run_api_test_1"
    assert data["status"] == "RUNNING"


def test_cancel_run_control(client):
    db_mgr = init_db("sqlite:///:memory:")
    with db_mgr.get_session() as s:
        run = AgentRunRecord(
            id="run_cancel_test",
            run_type=RunType.INITIAL_AUTHORING,
            status=RunStatus.RUNNING,
            repo="mathlingua/mathlore",
            issue_number=99,
        )
        s.add(run)
        s.commit()

    resp = client.post("/api/runs/run_cancel_test/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp_check = client.get("/api/runs/run_cancel_test")
    assert resp_check.json()["status"] == "CANCELLED"
