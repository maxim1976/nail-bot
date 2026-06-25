from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

import zoneinfo

import respx
from httpx import Response

from app.db import session_scope
from app.models import StudioProfile

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def _set_profile(
    *,
    access_token: str = "acc",
    refresh_token: str = "ref",
    expiry_future: bool = True,
) -> None:
    expiry = datetime.now(timezone.utc) + timedelta(hours=1 if expiry_future else -1)
    with session_scope() as s:
        p = s.get(StudioProfile, 1)
        if p is None:
            p = StudioProfile(id=1, studio_name="Test")
            s.add(p)
        p.google_access_token = access_token
        p.google_refresh_token = refresh_token
        p.google_token_expiry = expiry


def test_is_connected_false_when_no_profile():
    from app.google_calendar import is_connected
    assert is_connected() is False


def test_is_connected_true_when_refresh_token_set():
    from app.google_calendar import is_connected
    _set_profile()
    assert is_connected() is True


def test_create_event_returns_none_when_not_connected():
    from app.google_calendar import create_event
    result = create_event(
        service_name="Gel Nails",
        scheduled_at=datetime(2026, 7, 1, 14, 0, tzinfo=TZ),
        duration_min=90,
        customer_name="Alice",
        notes="",
    )
    assert result is None


@respx.mock
def test_create_event_returns_event_id():
    _set_profile(access_token="valid-token", expiry_future=True)
    respx.post("https://www.googleapis.com/calendar/v3/calendars/primary/events").mock(
        return_value=Response(200, json={"id": "evt_abc123"})
    )

    from app.google_calendar import create_event
    event_id = create_event(
        service_name="Gel Nails",
        scheduled_at=datetime(2026, 7, 1, 14, 0, tzinfo=TZ),
        duration_min=90,
        customer_name="Alice",
        notes="No extensions",
    )
    assert event_id == "evt_abc123"


@respx.mock
def test_create_event_refreshes_expired_token():
    _set_profile(access_token="old-token", expiry_future=False)
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(200, json={"access_token": "new-token", "expires_in": 3600})
    )
    respx.post("https://www.googleapis.com/calendar/v3/calendars/primary/events").mock(
        return_value=Response(200, json={"id": "evt_refreshed"})
    )

    from app.google_calendar import create_event
    event_id = create_event(
        service_name="Gel Nails",
        scheduled_at=datetime(2026, 7, 1, 14, 0, tzinfo=TZ),
        duration_min=60,
        customer_name="Bob",
        notes="",
    )
    assert event_id == "evt_refreshed"


@respx.mock
def test_delete_event_calls_api():
    _set_profile(expiry_future=True)
    respx.delete("https://www.googleapis.com/calendar/v3/calendars/primary/events/evt_abc123").mock(
        return_value=Response(204)
    )

    from app.google_calendar import delete_event
    delete_event("evt_abc123")  # should not raise


@respx.mock
def test_delete_event_ignores_404():
    _set_profile(expiry_future=True)
    respx.delete("https://www.googleapis.com/calendar/v3/calendars/primary/events/evt_gone").mock(
        return_value=Response(404)
    )

    from app.google_calendar import delete_event
    delete_event("evt_gone")  # should not raise
