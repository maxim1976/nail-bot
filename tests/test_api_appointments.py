from __future__ import annotations

import uuid
from datetime import date, datetime, time
import zoneinfo

from fastapi.testclient import TestClient

from app.db import session_scope
from app.main import app
from app.models import Service, User, WeeklyTemplate

TZ = zoneinfo.ZoneInfo("Asia/Taipei")
client = TestClient(app)


def _setup_service(duration_min: int = 90) -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name="Gel", name_en="Gel",
            name_tl="", name_id="", name_vi="",
            duration_min=duration_min, price=800, is_available=True,
        ))
    return svc_id


def _setup_user(uid: str = "U_appt") -> None:
    with session_scope() as s:
        if s.get(User, uid) is None:
            s.add(User(line_user_id=uid))


def _setup_template(dow: int) -> None:
    with session_scope() as s:
        s.merge(WeeklyTemplate(
            dow=dow, start_time=time(10, 0), end_time=time(18, 0),
            slot_duration_min=90, is_active=True,
        ))


def test_get_slots_no_template():
    svc_id = _setup_service()
    resp = client.get(f"/api/slots?service_id={svc_id}&date=2026-06-22")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_slots_with_template():
    svc_id = _setup_service(90)
    _setup_template(date(2026, 6, 23).weekday())  # Tuesday
    resp = client.get(f"/api/slots?service_id={svc_id}&date=2026-06-23")
    assert resp.status_code == 200
    slots = resp.json()
    assert len(slots) > 0
    assert "start" in slots[0]


def test_create_appointment_success():
    svc_id = _setup_service(90)
    _setup_user()
    _setup_template(date(2026, 6, 25).weekday())  # Thursday
    slot_dt = datetime(2026, 6, 25, 10, 0, tzinfo=TZ)
    resp = client.post("/api/appointments", json={
        "line_user_id": "U_appt",
        "service_id": str(svc_id),
        "scheduled_at": slot_dt.isoformat(),
        "customer_name": "Alice",
        "notes": None,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "confirmed"
    assert data["customer_name"] == "Alice"


def test_create_appointment_conflict():
    svc_id = _setup_service(90)
    _setup_user()
    _setup_template(date(2026, 6, 26).weekday())  # Friday
    slot_dt = datetime(2026, 6, 26, 10, 0, tzinfo=TZ)
    # First booking succeeds
    client.post("/api/appointments", json={
        "line_user_id": "U_appt",
        "service_id": str(svc_id),
        "scheduled_at": slot_dt.isoformat(),
        "customer_name": "Alice",
    })
    # Second booking for same slot fails
    resp = client.post("/api/appointments", json={
        "line_user_id": "U_appt",
        "service_id": str(svc_id),
        "scheduled_at": slot_dt.isoformat(),
        "customer_name": "Bob",
    })
    assert resp.status_code == 409


def test_my_appointments_empty():
    resp = client.get("/api/my-appointments?line_user_id=U_nobody")
    assert resp.status_code == 200
    assert resp.json() == []
