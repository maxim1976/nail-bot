import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("ADMIN_USERNAME", "admin")

import uuid
import zoneinfo
from datetime import datetime
from unittest.mock import MagicMock, patch

from freezegun import freeze_time

from app.cron import send_24h_reminders
from app.db import session_scope
from app.models import Appointment, Service, User

_TZ = zoneinfo.ZoneInfo("Asia/Taipei")

# Frozen "now": 2026-01-15 10:00 Taipei = 2026-01-15 02:00 UTC
_FROZEN_NOW = "2026-01-15 02:00:00"
# Appointment at 2026-01-16 10:00 Taipei — exactly 24h later, inside window
_APPT_AT = datetime(2026, 1, 16, 10, 0, 0, tzinfo=_TZ)


def _seed(*, status: str = "confirmed", reminder_sent: bool = False) -> uuid.UUID:
    svc_id = uuid.uuid4()
    appt_id = uuid.uuid4()
    with session_scope() as s:
        s.merge(User(
            line_user_id="U_test_reminder",
            display_name="Test User",
            preferred_language="zh",
        ))
        s.add(Service(
            id=svc_id,
            name="凝膠",
            duration_min=90,
            price=800,
            category="gel",
            sort_order=0,
        ))
        s.add(Appointment(
            id=appt_id,
            line_user_id="U_test_reminder",
            service_id=svc_id,
            scheduled_at=_APPT_AT,
            duration_min=90,
            status=status,
            customer_name="Test User",
            reminder_sent=reminder_sent,
        ))
    return appt_id


@freeze_time(_FROZEN_NOW)
def test_sends_reminder_and_marks_sent():
    appt_id = _seed()

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc
        send_24h_reminders()

    mock_lc.push.assert_called_once()
    call_kwargs = mock_lc.push.call_args.kwargs
    assert call_kwargs["line_user_id"] == "U_test_reminder"

    with session_scope() as s:
        appt = s.get(Appointment, appt_id)
        assert appt.reminder_sent is True


@freeze_time(_FROZEN_NOW)
def test_skips_already_reminded():
    _seed(reminder_sent=True)

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc
        send_24h_reminders()

    mock_lc.push.assert_not_called()


@freeze_time(_FROZEN_NOW)
def test_skips_cancelled_appointment():
    _seed(status="cancelled")

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc
        send_24h_reminders()

    mock_lc.push.assert_not_called()


@freeze_time("2026-01-15 02:00:00")  # now = 10:00 Taipei
def test_outside_window_not_reminded():
    # Appointment 48h away — outside the 23-25h window
    svc_id = uuid.uuid4()
    appt_id = uuid.uuid4()
    far_appt = datetime(2026, 1, 17, 10, 0, 0, tzinfo=_TZ)
    with session_scope() as s:
        s.merge(User(line_user_id="U_far", display_name="Far", preferred_language="en"))
        s.add(Service(id=svc_id, name="Gel", duration_min=60, price=600, category="gel", sort_order=1))
        s.add(Appointment(
            id=appt_id,
            line_user_id="U_far",
            service_id=svc_id,
            scheduled_at=far_appt,
            duration_min=60,
            status="confirmed",
            customer_name="Far User",
            reminder_sent=False,
        ))

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc
        send_24h_reminders()

    mock_lc.push.assert_not_called()


@freeze_time(_FROZEN_NOW)
def test_reminder_uses_customer_language():
    """Push message content differs by language — verify en template fires for en user."""
    svc_id = uuid.uuid4()
    appt_id = uuid.uuid4()
    with session_scope() as s:
        s.merge(User(line_user_id="U_en", display_name="En User", preferred_language="en"))
        s.add(Service(id=svc_id, name="Nail Art", duration_min=60, price=600, category="art", sort_order=2))
        s.add(Appointment(
            id=appt_id,
            line_user_id="U_en",
            service_id=svc_id,
            scheduled_at=_APPT_AT,
            duration_min=60,
            status="confirmed",
            customer_name="En User",
            reminder_sent=False,
        ))

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        MockClient.return_value = mock_lc
        send_24h_reminders()

    mock_lc.push.assert_called_once()
    msg_text = mock_lc.push.call_args.kwargs["messages"][0].payload["text"]
    assert "tomorrow" in msg_text.lower() or "Reminder" in msg_text


@freeze_time(_FROZEN_NOW)
def test_push_failure_does_not_block_subsequent_reminders():
    """If push fails for one appointment, others should still be reminded."""
    svc_id1, svc_id2 = uuid.uuid4(), uuid.uuid4()
    appt_id1, appt_id2 = uuid.uuid4(), uuid.uuid4()
    with session_scope() as s:
        s.merge(User(line_user_id="U_fail1", display_name="Fail1", preferred_language="zh"))
        s.merge(User(line_user_id="U_ok2", display_name="Ok2", preferred_language="zh"))
        s.add(Service(id=svc_id1, name="S1", duration_min=60, price=500, category="gel", sort_order=3))
        s.add(Service(id=svc_id2, name="S2", duration_min=60, price=500, category="gel", sort_order=4))
        s.add(Appointment(id=appt_id1, line_user_id="U_fail1", service_id=svc_id1,
                          scheduled_at=_APPT_AT, duration_min=60, status="confirmed",
                          customer_name="Fail1", reminder_sent=False))
        s.add(Appointment(id=appt_id2, line_user_id="U_ok2", service_id=svc_id2,
                          scheduled_at=_APPT_AT, duration_min=60, status="confirmed",
                          customer_name="Ok2", reminder_sent=False))

    call_count = 0
    def push_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs["line_user_id"] == "U_fail1":
            raise Exception("LINE API error")

    with patch("app.cron.LineClient") as MockClient:
        mock_lc = MagicMock()
        mock_lc.push.side_effect = push_side_effect
        MockClient.return_value = mock_lc
        send_24h_reminders()

    assert call_count == 2  # both attempted
    with session_scope() as s:
        appt1 = s.get(Appointment, appt_id1)
        appt2 = s.get(Appointment, appt_id2)
        assert appt1.reminder_sent is False  # failed push — not marked
        assert appt2.reminder_sent is True   # succeeded
