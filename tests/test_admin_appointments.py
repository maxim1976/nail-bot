from __future__ import annotations

import time
import uuid
import zoneinfo
from datetime import datetime

import jwt
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import session_scope
from app.main import app
from app.models import Appointment, Service, User

client = TestClient(app)
TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_appointment(*, scheduled_at: datetime, status: str = "confirmed") -> str:
    appt_id = uuid.uuid4()
    with session_scope() as s:
        svc_id = uuid.uuid4()
        s.add(Service(
            id=svc_id, name="Gel", name_en="Gel",
            name_tl="", name_id="", name_vi="",
            duration_min=90, price=800,
        ))
        s.merge(User(line_user_id="U_admin_test"))
        s.flush()
        s.add(Appointment(
            id=appt_id,
            line_user_id="U_admin_test",
            service_id=svc_id,
            scheduled_at=scheduled_at,
            duration_min=90,
            customer_name="Test",
            status=status,
        ))
    return str(appt_id)


def test_list_appointments_empty():
    resp = client.get("/admin/appointments", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_appointments_returns_all():
    _seed_appointment(scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=TZ))
    _seed_appointment(scheduled_at=datetime(2026, 8, 2, 10, 0, tzinfo=TZ))
    resp = client.get("/admin/appointments", headers=_auth())
    assert len(resp.json()) == 2


def test_list_appointments_filter_by_status():
    _seed_appointment(scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=TZ), status="confirmed")
    _seed_appointment(scheduled_at=datetime(2026, 8, 2, 10, 0, tzinfo=TZ), status="cancelled")
    resp = client.get("/admin/appointments?status=confirmed", headers=_auth())
    data = resp.json()
    assert all(a["status"] == "confirmed" for a in data)


def test_list_appointments_filter_by_date_range():
    _seed_appointment(scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=TZ))
    _seed_appointment(scheduled_at=datetime(2026, 9, 1, 10, 0, tzinfo=TZ))
    resp = client.get("/admin/appointments?from_date=2026-08-01&to_date=2026-08-31", headers=_auth())
    data = resp.json()
    assert len(data) == 1


def test_update_appointment_status():
    appt_id = _seed_appointment(scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=TZ))
    resp = client.put(f"/admin/appointments/{appt_id}", json={"status": "completed"}, headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_update_appointment_invalid_status():
    appt_id = _seed_appointment(scheduled_at=datetime(2026, 8, 1, 10, 0, tzinfo=TZ))
    resp = client.put(f"/admin/appointments/{appt_id}", json={"status": "pending"}, headers=_auth())
    assert resp.status_code == 422


def test_update_appointment_not_found():
    resp = client.put(f"/admin/appointments/{uuid.uuid4()}", json={"status": "completed"}, headers=_auth())
    assert resp.status_code == 404


def test_appointments_requires_auth():
    resp = client.get("/admin/appointments")
    assert resp.status_code == 403
