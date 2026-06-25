import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import json
import uuid
import zoneinfo
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.agent_tools import BOOKING_TOOLS, execute_tool
from app.db import session_scope
from app.models import Appointment, Service, User

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def _seed_user(line_user_id: str = "U_tool_test") -> None:
    with session_scope() as s:
        s.merge(User(line_user_id=line_user_id, display_name="Test", preferred_language="zh"))


def _seed_service(name: str = "Gel", duration_min: int = 90, price: int = 800) -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name=name, name_en="Gel",
            duration_min=duration_min, price=price, category="gel", sort_order=0,
        ))
    return svc_id


def _seed_appointment(
    line_user_id: str,
    svc_id: uuid.UUID,
    *,
    status: str = "confirmed",
    hours_from_now: int = 24,
) -> uuid.UUID:
    appt_id = uuid.uuid4()
    scheduled = datetime.now(tz=TZ) + timedelta(hours=hours_from_now)
    with session_scope() as s:
        s.add(Appointment(
            id=appt_id,
            line_user_id=line_user_id,
            service_id=svc_id,
            scheduled_at=scheduled,
            duration_min=90,
            status=status,
            customer_name="Test",
        ))
    return appt_id


def test_booking_tools_has_five_entries():
    names = [t["name"] for t in BOOKING_TOOLS]
    assert names == ["book_appointment", "get_my_appointments", "cancel_appointment", "get_services", "get_available_slots"]


def test_get_my_appointments_returns_upcoming():
    _seed_user()
    svc_id = _seed_service()
    _seed_appointment("U_tool_test", svc_id)

    result = json.loads(execute_tool("get_my_appointments", {}, line_user_id="U_tool_test"))
    assert len(result["appointments"]) == 1
    assert result["appointments"][0]["service"] == "Gel"


def test_get_my_appointments_excludes_past():
    _seed_user()
    svc_id = _seed_service()
    _seed_appointment("U_tool_test", svc_id, hours_from_now=-1)

    result = json.loads(execute_tool("get_my_appointments", {}, line_user_id="U_tool_test"))
    assert result["appointments"] == []


def test_get_my_appointments_excludes_cancelled():
    _seed_user()
    svc_id = _seed_service()
    _seed_appointment("U_tool_test", svc_id, status="cancelled")

    result = json.loads(execute_tool("get_my_appointments", {}, line_user_id="U_tool_test"))
    assert result["appointments"] == []


def test_cancel_appointment_success():
    _seed_user()
    svc_id = _seed_service()
    appt_id = _seed_appointment("U_tool_test", svc_id)

    with patch("app.agent_tools.LineClient") as MockLC:
        mock_lc = MagicMock()
        MockLC.return_value = mock_lc
        result = json.loads(
            execute_tool("cancel_appointment", {"appointment_id": str(appt_id)}, line_user_id="U_tool_test")
        )

    assert result["success"] is True
    mock_lc.push.assert_called_once()
    with session_scope() as s:
        appt = s.get(Appointment, appt_id)
        assert appt.status == "cancelled"


def test_cancel_appointment_not_owned_returns_error():
    _seed_user("U_tool_test")
    _seed_user("U_other")
    svc_id = _seed_service()
    appt_id = _seed_appointment("U_other", svc_id)

    with patch("app.agent_tools.LineClient"):
        result = json.loads(
            execute_tool("cancel_appointment", {"appointment_id": str(appt_id)}, line_user_id="U_tool_test")
        )
    assert "error" in result


def test_cancel_appointment_invalid_uuid_returns_error():
    result = json.loads(
        execute_tool("cancel_appointment", {"appointment_id": "not-a-uuid"}, line_user_id="U_tool_test")
    )
    assert "error" in result


def test_get_services_returns_available():
    svc_id = _seed_service("Nail Art", 60, 600)

    result = json.loads(execute_tool("get_services", {}, line_user_id="U_tool_test"))
    ids = [s["id"] for s in result["services"]]
    assert str(svc_id) in ids


def test_get_available_slots_valid_date():
    import app.slots as slots_mod

    with patch.object(slots_mod, "available_slots", return_value=[
        datetime(2026, 7, 1, 9, 0, tzinfo=TZ),
        datetime(2026, 7, 1, 10, 30, tzinfo=TZ),
    ]):
        result = json.loads(execute_tool("get_available_slots", {"date": "2026-07-01"}, line_user_id="U_tool_test"))
    assert result["slots"] == ["09:00", "10:30"]


def test_get_available_slots_invalid_date_returns_error():
    result = json.loads(execute_tool("get_available_slots", {"date": "not-a-date"}, line_user_id="U_tool_test"))
    assert "error" in result


def test_execute_tool_unknown_returns_error():
    result = json.loads(execute_tool("unknown_tool", {}, line_user_id="U_tool_test"))
    assert "error" in result
