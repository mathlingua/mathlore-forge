"""Tests for Google OAuth 2.0 authentication and Dominic Kramer authorization guard."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mathlore_forge.web.app import create_app
from mathlore_forge.web.auth import (
    ALLOWED_EMAIL,
    create_session_token,
    verify_session_token,
)


def test_session_token_roundtrip():
    token = create_session_token("DominicKramer@gmail.com", "Dominic Kramer")
    data = verify_session_token(token)
    assert data is not None
    assert data["email"] == "dominickramer@gmail.com"
    assert data["name"] == "Dominic Kramer"


def test_session_token_tampering():
    token = create_session_token("DominicKramer@gmail.com")
    tampered = token + "xyz"
    assert verify_session_token(tampered) is None


def test_authorization_guard_rejects_unauthorized_user():
    app = create_app()
    client = TestClient(app)

    # 1. Unauthenticated request to protected API endpoint
    resp = client.get("/api/runs")
    assert resp.status_code == 401

    # 2. Authenticated with non-Dominic email -> 403 Forbidden
    unauthorized_token = create_session_token("someone_else@gmail.com", "Intruder")
    client.cookies.set("forge_session", unauthorized_token)
    resp = client.get("/api/runs")
    assert resp.status_code == 403
    assert "DominicKramer@gmail.com" in resp.json()["detail"]

    # 3. Authenticated as DominicKramer@gmail.com -> Allowed (200 OK)
    authorized_token = create_session_token("DominicKramer@gmail.com", "Dominic Kramer")
    client.cookies.set("forge_session", authorized_token)
    resp = client.get("/api/runs")
    assert resp.status_code == 200
