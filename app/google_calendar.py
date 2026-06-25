from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta, timezone

import httpx

from app.db import session_scope
from app.models import StudioProfile

TZ = zoneinfo.ZoneInfo("Asia/Taipei")
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def is_connected() -> bool:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        return bool(profile and profile.google_refresh_token)


def _get_access_token() -> str | None:
    """Return a valid access token, refreshing if needed. Returns None if not connected."""
    from app.config import get_settings

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if not profile or not profile.google_refresh_token:
            return None
        now = datetime.now(timezone.utc)
        expiry = profile.google_token_expiry
        refresh_token = profile.google_refresh_token
        access_token = profile.google_access_token

    if expiry and expiry > now + timedelta(seconds=60):
        return access_token

    settings = get_settings()
    resp = httpx.post(_TOKEN_URL, data={
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    data = resp.json()
    new_token = data["access_token"]
    new_expiry = now + timedelta(seconds=data.get("expires_in", 3600))

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if profile:
            profile.google_access_token = new_token
            profile.google_token_expiry = new_expiry

    return new_token


def create_event(
    *,
    service_name: str,
    scheduled_at: datetime,
    duration_min: int,
    customer_name: str,
    notes: str,
) -> str | None:
    """Create a Google Calendar event. Returns event ID or None if not connected."""
    token = _get_access_token()
    if not token:
        return None

    start = scheduled_at.astimezone(TZ)
    end = start + timedelta(minutes=duration_min)
    description = f"Customer: {customer_name}"
    if notes:
        description += f"\nNotes: {notes}"

    resp = httpx.post(
        _EVENTS_URL,
        json={
            "summary": f"{service_name} — {customer_name}",
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Taipei"},
            "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Taipei"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json().get("id")


def delete_event(event_id: str) -> None:
    """Delete a Google Calendar event. Silently ignores if already deleted."""
    token = _get_access_token()
    if not token:
        return
    resp = httpx.delete(
        f"{_EVENTS_URL}/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 404:
        return
    resp.raise_for_status()
