from __future__ import annotations

import os
import time

import bcrypt
import jwt
from fastapi.testclient import TestClient

# Must set before TestClient(app) is created so Settings picks them up
_TEST_PASSWORD = "hualienvibe-admin"
_TEST_HASH = bcrypt.hashpw(_TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
os.environ["ADMIN_PASSWORD_HASH"] = _TEST_HASH

from app.config import get_settings
get_settings.cache_clear()

from app.main import app

client = TestClient(app)


def _make_token(*, sub: str = "admin", exp_offset: int = 3600) -> str:
    settings = get_settings()
    return jwt.encode(
        {"sub": sub, "exp": int(time.time()) + exp_offset},
        settings.admin_jwt_secret,
        algorithm="HS256",
    )


def test_login_success():
    resp = client.post("/admin/login", json={"username": "admin", "password": _TEST_PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    resp = client.post("/admin/login", json={"username": "admin", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_wrong_username():
    resp = client.post("/admin/login", json={"username": "notadmin", "password": _TEST_PASSWORD})
    assert resp.status_code == 401


def test_protected_route_requires_token():
    resp = client.get("/admin/studio")
    assert resp.status_code == 403


def test_protected_route_rejects_invalid_token():
    resp = client.get("/admin/studio", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert resp.status_code == 401


def test_protected_route_rejects_expired_token():
    token = _make_token(exp_offset=-1)  # already expired
    resp = client.get("/admin/studio", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_valid_token_passes_through():
    token = _make_token()
    # /admin/studio returns 404 when no studio row exists — that's fine, it means auth passed
    resp = client.get("/admin/studio", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 404)
