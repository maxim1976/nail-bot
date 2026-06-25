from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-gcal-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-gcal-secret")

import jwt
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import get_settings
from app.db import session_scope
from app.main import app
from app.models import StudioProfile

client = TestClient(app, follow_redirects=False)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _create_profile(**kwargs) -> None:
    with session_scope() as s:
        p = s.get(StudioProfile, 1)
        if p is None:
            p = StudioProfile(id=1, studio_name="Test")
            s.add(p)
        for k, v in kwargs.items():
            setattr(p, k, v)


def test_auth_url_requires_auth():
    resp = client.get("/admin/google/auth-url")
    assert resp.status_code == 403


def test_auth_url_returns_google_url():
    resp = client.get("/admin/google/auth-url", headers=_auth())
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert "accounts.google.com" in url
    assert "test-gcal-client-id" in url
    assert "calendar.events" in url


@respx.mock
def test_callback_stores_tokens_and_redirects():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(200, json={
            "access_token": "acc123",
            "refresh_token": "ref456",
            "expires_in": 3600,
        })
    )
    resp = client.get("/admin/google/callback?code=authcode123")
    assert resp.status_code in (302, 307)
    assert "/dashboard/" in resp.headers["location"]

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        assert profile.google_refresh_token == "ref456"
        assert profile.google_access_token == "acc123"


def test_disconnect_clears_tokens():
    _create_profile(
        google_access_token="acc",
        google_refresh_token="ref",
        google_token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    resp = client.delete("/admin/google/disconnect", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["disconnected"] is True

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        assert profile.google_refresh_token is None
        assert profile.google_access_token is None


def test_status_disconnected_when_no_profile():
    resp = client.get("/admin/google/status", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "email": None}


@respx.mock
def test_status_connected_with_email():
    _create_profile(
        google_access_token="acc",
        google_refresh_token="ref",
        google_token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
        return_value=Response(200, json={"email": "owner@gmail.com"})
    )
    resp = client.get("/admin/google/status", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["email"] == "owner@gmail.com"
