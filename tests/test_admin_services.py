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
from app.models import Appointment, Service

client = TestClient(app)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


_SVC_BODY = {
    "name": "凝膠美甲",
    "name_en": "Gel Nails",
    "name_tl": "Gel Nails",
    "name_id": "Gel Nails",
    "name_vi": "Gel Nails",
    "duration_min": 90,
    "price": 800,
}


def test_list_services_empty():
    resp = client.get("/admin/services", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_service():
    resp = client.post("/admin/services", json=_SVC_BODY, headers=_auth())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "凝膠美甲"
    assert data["duration_min"] == 90
    assert "id" in data


def test_list_services_returns_all():
    client.post("/admin/services", json=_SVC_BODY, headers=_auth())
    client.post("/admin/services", json={**_SVC_BODY, "name": "手繪彩繪", "is_available": False}, headers=_auth())
    resp = client.get("/admin/services", headers=_auth())
    assert len(resp.json()) == 2  # admin sees unavailable too


def test_update_service():
    r = client.post("/admin/services", json=_SVC_BODY, headers=_auth())
    svc_id = r.json()["id"]
    resp = client.put(f"/admin/services/{svc_id}", json={**_SVC_BODY, "price": 1200}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["price"] == 1200


def test_update_service_not_found():
    resp = client.put(f"/admin/services/{uuid.uuid4()}", json=_SVC_BODY, headers=_auth())
    assert resp.status_code == 404


def test_delete_service():
    r = client.post("/admin/services", json=_SVC_BODY, headers=_auth())
    svc_id = r.json()["id"]
    resp = client.delete(f"/admin/services/{svc_id}", headers=_auth())
    assert resp.status_code == 204
    assert client.get("/admin/services", headers=_auth()).json() == []


def test_delete_service_with_appointment_returns_409():
    r = client.post("/admin/services", json=_SVC_BODY, headers=_auth())
    svc_id = r.json()["id"]
    from datetime import datetime, timezone
    with session_scope() as s:
        from app.models import User
        s.merge(User(line_user_id="U_test_admin"))
        s.flush()
        s.add(Appointment(
            line_user_id="U_test_admin",
            service_id=uuid.UUID(svc_id),
            scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
            duration_min=90,
            customer_name="Test",
            status="confirmed",
        ))
    resp = client.delete(f"/admin/services/{svc_id}", headers=_auth())
    assert resp.status_code == 409


def test_services_requires_auth():
    resp = client.get("/admin/services")
    assert resp.status_code == 403
