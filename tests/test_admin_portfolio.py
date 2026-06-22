from __future__ import annotations

import os
import time
import uuid

# Set environment variables before importing app
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("ADMIN_USERNAME", "admin")

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import session_scope
from app.main import app
from app.models import Service

client = TestClient(app)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _create_service() -> str:
    with session_scope() as s:
        svc_id = uuid.uuid4()
        s.add(Service(
            id=svc_id, name="Gel", name_en="Gel",
            name_tl="", name_id="", name_vi="",
            duration_min=60, price=500,
        ))
    return str(svc_id)


_ITEM_BODY = {
    "title": "Spring Collection",
    "image_url": "https://cdn.example.com/spring.jpg",
}


def test_list_portfolio_empty():
    resp = client.get("/admin/portfolio", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_portfolio_item():
    resp = client.post("/admin/portfolio", json=_ITEM_BODY, headers=_auth())
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Spring Collection"
    assert data["is_visible"] is True
    assert "id" in data


def test_create_portfolio_item_with_service():
    svc_id = _create_service()
    body = {**_ITEM_BODY, "service_id": svc_id}
    resp = client.post("/admin/portfolio", json=body, headers=_auth())
    assert resp.status_code == 201
    assert resp.json()["service_id"] == svc_id


def test_update_portfolio_item():
    r = client.post("/admin/portfolio", json=_ITEM_BODY, headers=_auth())
    item_id = r.json()["id"]
    resp = client.put(
        f"/admin/portfolio/{item_id}",
        json={**_ITEM_BODY, "is_visible": False, "sort_order": 5},
        headers=_auth(),
    )
    assert resp.status_code == 200
    assert resp.json()["is_visible"] is False
    assert resp.json()["sort_order"] == 5


def test_update_portfolio_not_found():
    resp = client.put(f"/admin/portfolio/{uuid.uuid4()}", json=_ITEM_BODY, headers=_auth())
    assert resp.status_code == 404


def test_delete_portfolio_item():
    r = client.post("/admin/portfolio", json=_ITEM_BODY, headers=_auth())
    item_id = r.json()["id"]
    resp = client.delete(f"/admin/portfolio/{item_id}", headers=_auth())
    assert resp.status_code == 204
    assert client.get("/admin/portfolio", headers=_auth()).json() == []


def test_portfolio_requires_auth():
    resp = client.get("/admin/portfolio")
    assert resp.status_code == 403
