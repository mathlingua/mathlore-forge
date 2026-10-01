"""Tests for Curator Agent, intent classification, and curation planning flow."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from mathlore_forge.observability.notifications import NotificationService
from mathlore_forge.storage.db import AgentRunRecord, IssueRecord, PullRequestRecord, init_db
from mathlore_forge.web.app import create_app
from mathlore_forge.workflows.intent import IssueIntent, classify_issue_intent


@pytest.fixture(autouse=True)
def clean_test_db():
    db = init_db()
    with db.get_session() as s:
        s.query(IssueRecord).filter(IssueRecord.issue_number.in_([88, 89])).delete()
        s.query(AgentRunRecord).filter(AgentRunRecord.issue_number.in_([88, 89])).delete()
        s.query(PullRequestRecord).filter(PullRequestRecord.pr_number.in_([88, 89])).delete()
        s.commit()
    yield
    with db.get_session() as s:
        s.query(IssueRecord).filter(IssueRecord.issue_number.in_([88, 89])).delete()
        s.query(AgentRunRecord).filter(AgentRunRecord.issue_number.in_([88, 89])).delete()
        s.query(PullRequestRecord).filter(PullRequestRecord.pr_number.in_([88, 89])).delete()
        s.commit()


def test_classify_issue_intent_direct():
    intent = classify_issue_intent(
        title="[Forge] Add subset theorem",
        body="Please add theorem to 01_set_theory/04_operations.mlg stating A is subset of B",
        labels=["forge"],
    )
    assert intent == IssueIntent.DIRECT_AUTHORING


def test_classify_issue_intent_higher_order_planning():
    # Number theory content
    intent1 = classify_issue_intent(
        title="[Forge] Add more number theory content",
        body="I would like to add more number theory to mathlore.",
        labels=["forge"],
    )
    assert intent1 == IssueIntent.HIGHER_ORDER_PLANNING

    # Next logical chapter
    intent2 = classify_issue_intent(
        title="[Forge] Add the next logical chapter",
        body="Determine the next content that would coherently be added.",
        labels=["forge"],
    )
    assert intent2 == IssueIntent.HIGHER_ORDER_PLANNING

    # Restructure / tonal overhaul
    intent3 = classify_issue_intent(
        title="[Forge] Restructure chapter 02 and tonal changes",
        body="The prose needs an overhaul to be more intuitive.",
        labels=["forge"],
    )
    assert intent3 == IssueIntent.HIGHER_ORDER_PLANNING

    # Explicit plan label
    intent4 = classify_issue_intent(
        title="[Forge] Topological spaces",
        body="Introduce topologies.",
        labels=["forge", "plan"],
    )
    assert intent4 == IssueIntent.HIGHER_ORDER_PLANNING


def test_webhook_routes_abstract_issue_to_curation_planning():
    app = create_app()
    client = TestClient(app)

    payload = {
        "action": "opened",
        "issue": {
            "number": 88,
            "title": "[Forge] I want to add more number theory content",
            "body": "System should determine on its own what to add.",
            "user": {"login": "DominicKramer"},
            "labels": [{"name": "forge"}],
        },
        "sender": {"login": "DominicKramer"},
        "repository": {"full_name": "mathlingua/mathlore"},
    }

    with patch("mathlore_forge.web.routes.webhooks._run_curation_planning_task") as mock_task:
        resp = client.post(
            "/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "issues"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["workflow"] == "curation_planning"
        assert data["issue"] == 88


def test_webhook_routes_forge_execute_command():
    app = create_app()
    client = TestClient(app)

    payload = {
        "action": "created",
        "comment": {
            "body": "/forge execute",
            "user": {"login": "DominicKramer"},
        },
        "issue": {
            "number": 88,
            "title": "[Forge] Add number theory",
            # Note: No "pull_request" key -> it is an Issue comment!
        },
        "sender": {"login": "DominicKramer"},
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
        assert data["issue"] == 88


def test_notification_service():
    service = NotificationService()
    assert service.recipient_email == "DominicKramer@gmail.com"

    # Verify notification formatting without raising
    service.notify_plan_ready(
        repo="mathlingua/mathlore",
        issue_number=42,
        issue_title="Add number theory",
        revision=1,
    )

    service.notify_plan_approved(
        repo="mathlingua/mathlore",
        issue_number=42,
        issue_title="Add number theory",
    )
