"""Tests for GitHub webhook routing and dispatching."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from mathlore_forge.web.app import create_app


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
