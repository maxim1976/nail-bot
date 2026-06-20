from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta
import zoneinfo

import pytest

from app.db import session_scope
from app.models import Appointment, DateOverride, Service, User, WeeklyTemplate
from app.slots import available_slots

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def _make_service(duration_min: int = 90) -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name="Test", name_en="Test",
            name_tl="", name_id="", name_vi="",
            duration_min=duration_min, price=800,
        ))
    return svc_id


def _make_template(dow: int, start: time, end: time, slot_min: int = 90) -> None:
    with session_scope() as s:
        s.merge(WeeklyTemplate(
            dow=dow, start_time=start, end_time=end,
            slot_duration_min=slot_min, is_active=True,
        ))


def _make_user() -> str:
    uid = "U_slot_test"
    with session_scope() as s:
        existing = s.get(User, uid)
        if existing is None:
            s.add(User(line_user_id=uid))
    return uid


def _book(svc_id: uuid.UUID, dt: datetime, duration_min: int = 90) -> None:
    uid = _make_user()
    with session_scope() as s:
        s.add(Appointment(
            line_user_id=uid,
            service_id=svc_id,
            scheduled_at=dt,
            duration_min=duration_min,
            status="confirmed",
            customer_name="Test",
        ))


def test_no_template_returns_empty():
    svc_id = _make_service()
    # Monday 2026-06-22, no template set
    result = available_slots(date(2026, 6, 22), svc_id, duration_min=90)
    assert result == []


def test_inactive_template_returns_empty():
    svc_id = _make_service()
    dow = date(2026, 6, 22).weekday()  # Monday = 0
    with session_scope() as s:
        s.merge(WeeklyTemplate(
            dow=dow, start_time=time(10, 0), end_time=time(18, 0),
            slot_duration_min=90, is_active=False,
        ))
    result = available_slots(date(2026, 6, 22), svc_id, duration_min=90)
    assert result == []


def test_returns_correct_slots():
    # Tuesday 2026-06-23, 10:00-13:30, 90min slots → 10:00, 11:30 = 2 slots
    # (13:00 slot would end at 14:30 > 13:30, so it is excluded)
    svc_id = _make_service(90)
    dow = date(2026, 6, 23).weekday()  # Tuesday = 1
    _make_template(dow, time(10, 0), time(13, 30), 90)
    result = available_slots(date(2026, 6, 23), svc_id, duration_min=90)
    assert len(result) == 2
    assert result[0] == datetime(2026, 6, 23, 10, 0, tzinfo=TZ)
    assert result[1] == datetime(2026, 6, 23, 11, 30, tzinfo=TZ)


def test_booked_slot_excluded():
    svc_id = _make_service(90)
    dow = date(2026, 6, 24).weekday()  # Wednesday = 2
    _make_template(dow, time(10, 0), time(18, 0), 90)
    slot_dt = datetime(2026, 6, 24, 10, 0, tzinfo=TZ)
    _book(svc_id, slot_dt, 90)
    result = available_slots(date(2026, 6, 24), svc_id, duration_min=90)
    assert slot_dt not in result
    # 11:30 should still be available
    assert datetime(2026, 6, 24, 11, 30, tzinfo=TZ) in result


def test_blocked_date_override_returns_empty():
    svc_id = _make_service(90)
    target = date(2026, 6, 25)  # Thursday = 3
    dow = target.weekday()
    _make_template(dow, time(10, 0), time(18, 0), 90)
    with session_scope() as s:
        s.merge(DateOverride(date=target, is_blocked=True))
    result = available_slots(target, svc_id, duration_min=90)
    assert result == []


def test_custom_hours_date_override():
    svc_id = _make_service(90)
    target = date(2026, 6, 26)  # Friday = 4
    dow = target.weekday()
    _make_template(dow, time(10, 0), time(18, 0), 90)
    with session_scope() as s:
        s.merge(DateOverride(date=target, is_blocked=False,
                             custom_start=time(14, 0), custom_end=time(17, 30)))
    result = available_slots(target, svc_id, duration_min=90)
    assert result == [
        datetime(2026, 6, 26, 14, 0, tzinfo=TZ),
        datetime(2026, 6, 26, 15, 30, tzinfo=TZ),
    ]
