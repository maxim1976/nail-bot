from __future__ import annotations

import time

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_weekly_template_empty():
    resp = client.get("/admin/weekly-template", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_put_weekly_template_creates_row():
    body = {"start_time": "10:00:00", "end_time": "18:00:00", "slot_duration_min": 90, "is_active": True}
    resp = client.put("/admin/weekly-template/1", json=body, headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["dow"] == 1
    assert data["start_time"] == "10:00:00"
    assert data["is_active"] is True


def test_put_weekly_template_upserts():
    body = {"start_time": "09:00:00", "end_time": "17:00:00", "slot_duration_min": 60, "is_active": True}
    client.put("/admin/weekly-template/2", json=body, headers=_auth())
    body2 = {**body, "start_time": "10:00:00"}
    resp = client.put("/admin/weekly-template/2", json=body2, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["start_time"] == "10:00:00"
    # Only one row for dow=2
    rows = [r for r in client.get("/admin/weekly-template", headers=_auth()).json() if r["dow"] == 2]
    assert len(rows) == 1


def test_put_weekly_template_invalid_dow():
    body = {"start_time": "10:00:00", "end_time": "18:00:00", "slot_duration_min": 90, "is_active": True}
    resp = client.put("/admin/weekly-template/7", json=body, headers=_auth())
    assert resp.status_code == 422


def test_date_overrides_empty():
    resp = client.get("/admin/date-overrides", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_date_override_blocked():
    body = {"date": "2026-08-15", "is_blocked": True}
    resp = client.post("/admin/date-overrides", json=body, headers=_auth())
    assert resp.status_code == 201
    data = resp.json()
    assert data["date"] == "2026-08-15"
    assert data["is_blocked"] is True


def test_create_date_override_custom_hours():
    body = {"date": "2026-08-20", "is_blocked": False, "custom_start": "12:00:00", "custom_end": "16:00:00"}
    resp = client.post("/admin/date-overrides", json=body, headers=_auth())
    assert resp.status_code == 201
    data = resp.json()
    assert data["custom_start"] == "12:00:00"


def test_create_date_override_upserts():
    client.post("/admin/date-overrides", json={"date": "2026-09-01", "is_blocked": True}, headers=_auth())
    resp = client.post("/admin/date-overrides", json={"date": "2026-09-01", "is_blocked": False}, headers=_auth())
    assert resp.status_code == 201
    assert resp.json()["is_blocked"] is False
    rows = [r for r in client.get("/admin/date-overrides", headers=_auth()).json() if r["date"] == "2026-09-01"]
    assert len(rows) == 1


def test_delete_date_override():
    client.post("/admin/date-overrides", json={"date": "2026-10-01", "is_blocked": True}, headers=_auth())
    resp = client.delete("/admin/date-overrides/2026-10-01", headers=_auth())
    assert resp.status_code == 204
    rows = [r for r in client.get("/admin/date-overrides", headers=_auth()).json() if r["date"] == "2026-10-01"]
    assert rows == []


def test_delete_date_override_not_found():
    resp = client.delete("/admin/date-overrides/2026-12-25", headers=_auth())
    assert resp.status_code == 404


def test_schedule_requires_auth():
    resp = client.get("/admin/weekly-template")
    assert resp.status_code == 403
