"""Tests for GitHub webhook routing and dispatching."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from mathlore_forge.storage.db import AgentRunRecord, IssueRecord, PullRequestRecord, RunStatus, init_db
from mathlore_forge.web.app import create_app


@pytest.fixture(autouse=True)
def clean_test_db():
    db = init_db()
    with db.get_session() as s:
        s.query(IssueRecord).filter(IssueRecord.issue_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.query(AgentRunRecord).filter(AgentRunRecord.issue_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.query(PullRequestRecord).filter(PullRequestRecord.pr_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.commit()
    yield
    with db.get_session() as s:
        s.query(IssueRecord).filter(IssueRecord.issue_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.query(AgentRunRecord).filter(AgentRunRecord.issue_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.query(PullRequestRecord).filter(PullRequestRecord.pr_number.in_([55, 56, 57, 88, 99, 101, 102])).delete()
        s.commit()


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_issue_webhook_triggers_authoring(client):
    payload = {
        "action": "opened",
        "issue": {
            "number": 55,
            "title": "[Forge] Add quotient ring definition",
            "body": "Please add quotient ring to 03_rings.mlg",
            "user": {"login": "DominicKramer"},
            "labels": [{"name": "forge"}],
        },
        "sender": {"login": "DominicKramer"},
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_authoring_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issues"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "authoring"
        assert data["issue"] == 55


def test_unauthorized_user_issue_is_ignored(client):
    payload = {
        "action": "opened",
        "issue": {
            "number": 99,
            "title": "[Forge] Malicious request",
            "body": "Spam",
            "user": {"login": "random_user"},
            "labels": [{"name": "forge"}],
        },
        "sender": {"login": "random_user"},
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    resp = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "issues"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_pr_review_approval_triggers_flywheel(client):
    payload = {
        "action": "submitted",
        "pull_request": {
            "number": 56,
            "title": "[Forge] Add quotient ring definition",
        },
        "review": {
            "state": "approved",
            "user": {"login": "DominicKramer"},
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_flywheel_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "pull_request_review"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "flywheel_and_merge"
        assert data["pr"] == 56


def test_slash_command_comment_triggers_review(client):
    payload = {
        "action": "created",
        "comment": {
            "body": "/forge address please check line 40",
            "user": {"login": "DominicKramer"},
        },
        "issue": {
            "number": 56,
            "pull_request": {"url": "https://api.github.com/repos/mathlingua/mathlore/pulls/56"},
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_review_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "address_review_comments"


def test_slash_command_forge_accept_on_pr(client):
    payload = {
        "action": "created",
        "comment": {
            "body": "/forge accept",
            "user": {"login": "DominicKramer"},
        },
        "issue": {
            "number": 56,
            "pull_request": {"url": "https://api.github.com/repos/mathlingua/mathlore/pulls/56"},
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_flywheel_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "flywheel_and_merge"
        assert data["pr"] == 56


def test_slash_command_forge_accept_on_issue(client):
    payload = {
        "action": "created",
        "comment": {
            "body": "/forge accept",
            "user": {"login": "DominicKramer"},
        },
        "issue": {
            "number": 57,
            "title": "Axioms of Set Theory",
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_curation_execution_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issue_comment"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "curation_plan_execution"
        assert data["issue"] == 57


def test_pull_request_merged_closes_review_runs(client):
    db = init_db()
    with db.get_session() as s:
        # Seed an issue, PR, and awaiting-review run
        issue = IssueRecord(repo="mathlingua/mathlore", issue_number=101, title="Test Issue", status="AWAITING_PR_REVIEW")
        s.add(issue)
        s.flush()
        pr = PullRequestRecord(repo="mathlingua/mathlore", pr_number=101, branch_name="test-branch", title="Test PR", issue_id=issue.id, status="AWAITING_REVIEW")
        s.add(pr)
        s.flush()
        run = AgentRunRecord(id="run_test_101", repo="mathlingua/mathlore", issue_number=101, pr_number=101, issue_id=issue.id, status=RunStatus.AWAITING_REVIEW)
        s.add(run)
        s.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 101,
            "merged": True,
            "body": "Closes #101",
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    resp = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["merged"] is True

    # Verify DB records updated to COMPLETED / MERGED / RESOLVED
    with db.get_session() as s:
        r = s.query(AgentRunRecord).filter_by(id="run_test_101").first()
        assert r.status == RunStatus.COMPLETED
        p = s.query(PullRequestRecord).filter_by(pr_number=101).first()
        assert p.status == "MERGED"
        i = s.query(IssueRecord).filter_by(issue_number=101).first()
        assert i.status == "RESOLVED"
        assert i.plan_status == "COMPLETED"


def test_pull_request_closed_unmerged_cancels_runs(client):
    db = init_db()
    with db.get_session() as s:
        issue = IssueRecord(repo="mathlingua/mathlore", issue_number=102, title="Test Issue 102", status="AWAITING_PR_REVIEW")
        s.add(issue)
        s.flush()
        pr = PullRequestRecord(repo="mathlingua/mathlore", pr_number=102, branch_name="test-branch-102", title="Test PR 102", issue_id=issue.id, status="AWAITING_REVIEW")
        s.add(pr)
        s.flush()
        run = AgentRunRecord(id="run_test_102", repo="mathlingua/mathlore", issue_number=102, pr_number=102, issue_id=issue.id, status=RunStatus.AWAITING_REVIEW)
        s.add(run)
        s.commit()

    payload = {
        "action": "closed",
        "pull_request": {
            "number": 102,
            "merged": False,
            "body": "Closes #102",
        },
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    resp = client.post(
        "/webhooks/github",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
    assert resp.json()["merged"] is False

    with db.get_session() as s:
        r = s.query(AgentRunRecord).filter_by(id="run_test_102").first()
        assert r.status == RunStatus.CANCELLED
        p = s.query(PullRequestRecord).filter_by(pr_number=102).first()
        assert p.status == "CLOSED"
        i = s.query(IssueRecord).filter_by(issue_number=102).first()
        assert i.status == "CLOSED"


