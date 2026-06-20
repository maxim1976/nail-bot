from __future__ import annotations

import uuid
from datetime import datetime
import zoneinfo
from unittest.mock import MagicMock, call

import pytest

from app.notifications import send_booking_confirmation

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def _make_appt(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        line_user_id="U001",
        service_id=uuid.uuid4(),
        scheduled_at=datetime(2026, 7, 1, 10, 0, tzinfo=TZ),
        duration_min=90,
        status="confirmed",
        customer_name="Alice",
        notes=None,
    )
    defaults.update(kwargs)
    appt = MagicMock()
    for k, v in defaults.items():
        setattr(appt, k, v)
    return appt


def _make_service(name: str = "Gel Nails", price: int = 800):
    svc = MagicMock()
    svc.name = name
    svc.price = price
    return svc


def _make_user(lang: str = "zh", owner_line_user_id: str | None = None):
    user = MagicMock()
    user.preferred_language = lang
    return user


@pytest.fixture()
def line_client():
    return MagicMock()


def test_sends_push_to_customer(line_client):
    appt = _make_appt()
    send_booking_confirmation(
        appt=appt,
        service=_make_service(),
        user=_make_user(lang="zh"),
        line_client=line_client,
        owner_line_user_id=None,
    )
    assert line_client.push.call_count >= 1
    first_call_kwargs = line_client.push.call_args_list[0][1]
    assert first_call_kwargs["line_user_id"] == "U001"


def test_sends_push_to_owner_if_configured(line_client):
    appt = _make_appt()
    send_booking_confirmation(
        appt=appt,
        service=_make_service(),
        user=_make_user(),
        line_client=line_client,
        owner_line_user_id="U_owner",
    )
    assert line_client.push.call_count == 2
    owner_call = line_client.push.call_args_list[1][1]
    assert owner_call["line_user_id"] == "U_owner"


def test_no_owner_push_if_not_configured(line_client):
    appt = _make_appt()
    send_booking_confirmation(
        appt=appt,
        service=_make_service(),
        user=_make_user(),
        line_client=line_client,
        owner_line_user_id=None,
    )
    assert line_client.push.call_count == 1


def test_customer_message_in_english(line_client):
    appt = _make_appt()
    send_booking_confirmation(
        appt=appt,
        service=_make_service("Gel Nails"),
        user=_make_user(lang="en"),
        line_client=line_client,
        owner_line_user_id=None,
    )
    msg_text = line_client.push.call_args[1]["messages"][0].payload["text"]
    assert "Booking Confirmed" in msg_text, f"Expected 'Booking Confirmed' in: {msg_text!r}"
