"""Google OAuth 2.0 authentication with strict email authorization guard."""

from __future__ import annotations

import os
from typing import Any
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

ALLOWED_EMAIL = os.getenv("ALLOWED_ADMIN_EMAIL", "DominicKramer@gmail.com").strip().lower()
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "forge-dev-secret-key-change-in-prod-xyz123")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def create_session_token(email: str, name: str = "") -> str:
    """Generates a signed, tamper-proof session token."""
    return _serializer.dumps({"email": email.lower(), "name": name})


def verify_session_token(token: str, max_age: int = 86400 * 7) -> dict[str, Any] | None:
    """Verifies and decodes a session token."""
    try:
        data = _serializer.loads(token, max_age=max_age)
        if isinstance(data, dict) and data.get("email"):
            return data
    except (BadSignature, SignatureExpired):
        return None
    return None


def get_current_user(request: Request) -> dict[str, Any] | None:
    """Extracts authenticated user from signed session cookie or header."""
    # Check for session cookie
    token = request.cookies.get("forge_session")
    if token:
        user = verify_session_token(token)
        if user:
            return user

    # Optional dev mode bypass if explicitly configured
    if os.getenv("DEV_ALLOW_LOCAL_ADMIN") == "true":
        return {"email": ALLOWED_EMAIL, "name": "Dominic Kramer (Dev)"}

    return None


def require_admin_user(request: Request) -> dict[str, Any]:
    """Dependency that strictly enforces authentication as Dominic Kramer."""
    user = get_current_user(request)
    if not user:
        # Check if browser request
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with Google.",
        )

    if user.get("email", "").lower() != ALLOWED_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Only {ALLOWED_EMAIL} is authorized to access Mathlore Forge.",
        )

    return user


async def exchange_google_code(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchanges an authorization code for Google user profile."""
    token_url = "https://oauth2.googleapis.com/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15.0,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange Google OAuth code: {resp.text}",
            )
        data = resp.json()
        raw_id_token = data.get("id_token")

    if not raw_id_token:
        raise HTTPException(status_code=400, detail="Missing id_token in Google OAuth response")

    # Verify ID token
    try:
        claims = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Invalid Google ID token: {err}")

    email = claims.get("email", "").lower()
    if email != ALLOWED_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized account: {email}. Mathlore Forge is restricted strictly to {ALLOWED_EMAIL}.",
        )

    return {
        "email": email,
        "name": claims.get("name", ""),
        "picture": claims.get("picture", ""),
    }
