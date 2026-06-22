import os
os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("ADMIN_USERNAME", "admin")

import uuid
import zoneinfo
from datetime import datetime
from unittest.mock import MagicMock, patch

from freezegun import freeze_time

from app.cron import send_morning_summary
from app.db import session_scope
from app.models import Appointment, Service, User

_TZ = zoneinfo.ZoneInfo("Asia/Taipei")

# Frozen at 08:00 Taipei = 00:00 UTC on 2026-01-15
_FROZEN_NOW = "2026-01-15 00:00:00"
_TODAY_APPT = datetime(2026, 1, 15, 10, 0, 0, tzinfo=_TZ)
_TOMORROW_APPT = datetime(2026, 1, 16, 10, 0, 0, tzinfo=_TZ)


def _seed_today_appt() -> None:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.merge(User(line_user_id="U_owner_test", display_name="Owner", preferred_language="zh"))
        s.add(Service(id=svc_id, name="凝膠美甲", duration_min=90, price=800, category="gel", sort_order=0))
        s.add(Appointment(
            id=uuid.uuid4(),
            line_user_id="U_owner_test",
            service_id=svc_id,
            scheduled_at=_TODAY_APPT,
            duration_min=90,
            status="confirmed",
            customer_name="Alice",
            reminder_sent=False,
        ))


@freeze_time(_FROZEN_NOW)
def test_sends_summary_to_owner():
    _seed_today_appt()

    with patch("app.cron.LineClient") as MockClient, \
         patch("app.cron.get_settings") as mock_settings:
        mock_settings.return_value.line_channel_access_token = "test-token"
        mock_settings.return_value.owner_line_user_id = "U_studio_owner"
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc

        send_morning_summary()

    mock_lc.push.assert_called_once()
    call_kwargs = mock_lc.push.call_args.kwargs
    assert call_kwargs["line_user_id"] == "U_studio_owner"
    msg_text = call_kwargs["messages"][0].payload["text"]
    assert "Alice" in msg_text
    assert "凝膠美甲" in msg_text
    assert "10:00" in msg_text


@freeze_time(_FROZEN_NOW)
def test_sends_no_appointment_summary():
    # No appointments seeded — DB is empty due to _clean_db autouse

    with patch("app.cron.LineClient") as MockClient, \
         patch("app.cron.get_settings") as mock_settings:
        mock_settings.return_value.line_channel_access_token = "test-token"
        mock_settings.return_value.owner_line_user_id = "U_studio_owner"
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc

        send_morning_summary()

    mock_lc.push.assert_called_once()
    msg_text = mock_lc.push.call_args.kwargs["messages"][0].payload["text"]
    assert "無預約" in msg_text or "0" in msg_text


@freeze_time(_FROZEN_NOW)
def test_skips_when_no_owner_configured():
    _seed_today_appt()

    with patch("app.cron.LineClient") as MockClient, \
         patch("app.cron.get_settings") as mock_settings:
        mock_settings.return_value.line_channel_access_token = "test-token"
        mock_settings.return_value.owner_line_user_id = None
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc

        send_morning_summary()

    mock_lc.push.assert_not_called()


@freeze_time(_FROZEN_NOW)
def test_excludes_cancelled_appointments():
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.merge(User(line_user_id="U_cancelled", display_name="Cancelled", preferred_language="zh"))
        s.add(Service(id=svc_id, name="Test", duration_min=60, price=500, category="gel", sort_order=1))
        s.add(Appointment(
            id=uuid.uuid4(),
            line_user_id="U_cancelled",
            service_id=svc_id,
            scheduled_at=_TODAY_APPT,
            duration_min=60,
            status="cancelled",
            customer_name="Cancelled User",
            reminder_sent=False,
        ))

    with patch("app.cron.LineClient") as MockClient, \
         patch("app.cron.get_settings") as mock_settings:
        mock_settings.return_value.line_channel_access_token = "test-token"
        mock_settings.return_value.owner_line_user_id = "U_studio_owner"
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc

        send_morning_summary()

    msg_text = mock_lc.push.call_args.kwargs["messages"][0].payload["text"]
    assert "Cancelled User" not in msg_text


@freeze_time(_FROZEN_NOW)
def test_excludes_tomorrow_appointments():
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.merge(User(line_user_id="U_tomorrow", display_name="Tomorrow", preferred_language="zh"))
        s.add(Service(id=svc_id, name="Test2", duration_min=60, price=500, category="gel", sort_order=2))
        s.add(Appointment(
            id=uuid.uuid4(),
            line_user_id="U_tomorrow",
            service_id=svc_id,
            scheduled_at=_TOMORROW_APPT,
            duration_min=60,
            status="confirmed",
            customer_name="Tomorrow User",
            reminder_sent=False,
        ))

    with patch("app.cron.LineClient") as MockClient, \
         patch("app.cron.get_settings") as mock_settings:
        mock_settings.return_value.line_channel_access_token = "test-token"
        mock_settings.return_value.owner_line_user_id = "U_studio_owner"
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc

        send_morning_summary()

    msg_text = mock_lc.push.call_args.kwargs["messages"][0].payload["text"]
    assert "Tomorrow User" not in msg_text
