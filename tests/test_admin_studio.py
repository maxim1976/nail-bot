from __future__ import annotations

import os
import time

# Set environment variables before importing app
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("ADMIN_USERNAME", "admin")

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import session_scope
from app.main import app
from app.models import StudioProfile

client = TestClient(app)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_get_studio_404_when_not_set():
    resp = client.get("/admin/studio", headers=_auth())
    assert resp.status_code == 404


def test_put_studio_creates_profile():
    body = {
        "studio_name": "Hualienvibe Test",
        "owner_name": "Alice",
        "address": "台北市信義區",
        "phone": "+886912345678",
        "instagram": "@test",
        "cancellation_policy": "24h notice",
        "aftercare_notes": "Keep dry",
        "ai_persona_notes": "Friendly tone",
        "owner_line_user_id": "U_owner",
    }
    resp = client.put("/admin/studio", json=body, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["studio_name"] == "Hualienvibe Test"
    assert data["owner_name"] == "Alice"
    assert data["owner_line_user_id"] == "U_owner"


def test_put_studio_upserts():
    with session_scope() as s:
        s.add(StudioProfile(id=1, studio_name="Old Name"))
    resp = client.put("/admin/studio", json={"studio_name": "New Name"}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["studio_name"] == "New Name"


def test_get_studio_returns_after_put():
    client.put("/admin/studio", json={"studio_name": "Test Studio"}, headers=_auth())
    resp = client.get("/admin/studio", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["studio_name"] == "Test Studio"


def test_studio_requires_auth():
    resp = client.get("/admin/studio")
    assert resp.status_code == 403
