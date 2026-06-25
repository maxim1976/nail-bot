# Google Calendar Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically create/delete Google Calendar events when appointments are booked or cancelled, with OAuth connect/disconnect in the admin dashboard.

**Architecture:** Owner authenticates once via Google OAuth (stored in `StudioProfile`). `app/google_calendar.py` handles token refresh and Calendar API calls using `httpx`. Hooks in `agent_tools.py` and `admin/appointments.py` call create/delete after each booking/cancellation. Admin UI shows connection status below Studio Profile.

**Tech Stack:** Python `httpx` (already in deps, no new libraries needed), Google Calendar REST API v3, Google OAuth 2.0, Alpine.js (existing admin UI pattern)

## Global Constraints

- Python 3.12, FastAPI, SQLAlchemy 2.0 mapped columns pattern
- All Google API calls use `httpx` (already a dep) — do NOT add `google-auth` or `google-api-python-client`
- Google API failures on booking/cancel must be suppressed with `contextlib.suppress(Exception)` — never break LINE flow
- All new admin endpoints require `Depends(require_admin_token)` except `/admin/google/callback` (called by Google redirect, no token)
- Tests use `respx` (already in dev deps) for mocking HTTP calls to Google
- Run tests with: `pytest tests/ -x -q` from project root

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `app/google_calendar.py` | Token management, Calendar API calls |
| Create | `app/admin/google_calendar.py` | OAuth endpoints (auth-url, callback, disconnect, status) |
| Create | `alembic/versions/0003_google_calendar.py` | DB migration for new columns |
| Create | `tests/test_google_calendar.py` | Unit tests for google_calendar module |
| Create | `tests/test_admin_google_calendar.py` | Integration tests for admin OAuth endpoints |
| Modify | `app/models.py` | Add 3 cols to StudioProfile, 1 col to Appointment |
| Modify | `app/config.py` | Add `google_client_id`, `google_client_secret` settings |
| Modify | `app/admin/schemas.py` | Add `GoogleStatusOut` schema |
| Modify | `app/main.py` | Register google_calendar admin router |
| Modify | `app/agent_tools.py` | Call create_event in `_book_appointment`, delete_event in `_cancel_appointment` |
| Modify | `app/admin/appointments.py` | Call delete_event in `update_appointment` on cancel |
| Modify | `frontend/admin/index.html` | Google Calendar section below Studio Profile form |

---

## Task 1: DB Migration + Model + Config Changes

**Files:**
- Modify: `app/models.py`
- Modify: `app/config.py`
- Modify: `app/admin/schemas.py`
- Create: `alembic/versions/0003_google_calendar.py`

**Interfaces:**
- Produces: `StudioProfile.google_refresh_token`, `StudioProfile.google_access_token`, `StudioProfile.google_token_expiry`, `Appointment.google_calendar_event_id`, `Settings.google_client_id`, `Settings.google_client_secret`

- [ ] **Step 1: Add columns to `app/models.py`**

In `StudioProfile`, add after `owner_line_user_id`:
```python
google_access_token: Mapped[str | None] = mapped_column(String)
google_refresh_token: Mapped[str | None] = mapped_column(String)
google_token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

In `Appointment`, add after `notes`:
```python
google_calendar_event_id: Mapped[str | None] = mapped_column(String)
```

- [ ] **Step 2: Add settings to `app/config.py`**

Add inside `Settings` class, after `rich_menu_id`:
```python
google_client_id: str | None = None
google_client_secret: str | None = None
```

- [ ] **Step 3: Add `GoogleStatusOut` to `app/admin/schemas.py`**

Add at end of file:
```python
class GoogleStatusOut(BaseModel):
    connected: bool
    email: str | None = None
```

- [ ] **Step 4: Write migration `alembic/versions/0003_google_calendar.py`**

```python
"""add google calendar columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25

"""
from __future__ import annotations
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("studio_profile", sa.Column("google_access_token", sa.String(), nullable=True))
    op.add_column("studio_profile", sa.Column("google_refresh_token", sa.String(), nullable=True))
    op.add_column("studio_profile", sa.Column("google_token_expiry", sa.DateTime(timezone=True), nullable=True))
    op.add_column("appointments", sa.Column("google_calendar_event_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "google_calendar_event_id")
    op.drop_column("studio_profile", "google_token_expiry")
    op.drop_column("studio_profile", "google_refresh_token")
    op.drop_column("studio_profile", "google_access_token")
```

- [ ] **Step 5: Run existing tests to confirm nothing broke**

```bash
pytest tests/ -x -q
```
Expected: all pass (new columns are nullable, no existing tests affected)

- [ ] **Step 6: Commit**

```bash
git add app/models.py app/config.py app/admin/schemas.py alembic/versions/0003_google_calendar.py
git commit -m "feat: add google calendar columns to models and migration"
```

---

## Task 2: `app/google_calendar.py` — Core Module

**Files:**
- Create: `app/google_calendar.py`
- Create: `tests/test_google_calendar.py`

**Interfaces:**
- Consumes: `StudioProfile.google_refresh_token`, `StudioProfile.google_access_token`, `StudioProfile.google_token_expiry`, `Settings.google_client_id`, `Settings.google_client_secret`
- Produces:
  - `is_connected() -> bool`
  - `create_event(*, service_name: str, scheduled_at: datetime, duration_min: int, customer_name: str, notes: str) -> str | None` (returns Google event ID or None)
  - `delete_event(event_id: str) -> None`

- [ ] **Step 1: Write failing tests in `tests/test_google_calendar.py`**

```python
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import pytest
import respx
from httpx import Response

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")

import zoneinfo
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
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_google_calendar.py -x -q
```
Expected: `ModuleNotFoundError: No module named 'app.google_calendar'`

- [ ] **Step 3: Create `app/google_calendar.py`**

```python
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_google_calendar.py -x -q
```
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/google_calendar.py tests/test_google_calendar.py
git commit -m "feat: add google_calendar module with create/delete event and token refresh"
```

---

## Task 3: Admin OAuth Endpoints

**Files:**
- Create: `app/admin/google_calendar.py`
- Create: `tests/test_admin_google_calendar.py`
- Modify: `app/main.py` (register router)

**Interfaces:**
- Consumes: `GoogleStatusOut` from `app/admin/schemas`, `require_admin_token` from `app/admin/auth`, `StudioProfile` model, `Settings.google_client_id/secret/admin_base_url`
- Produces:
  - `GET /admin/google/auth-url` → `{"url": "https://accounts.google.com/..."}`
  - `GET /admin/google/callback?code=...` → redirect to `/dashboard/`
  - `DELETE /admin/google/disconnect` → `{"disconnected": true}`
  - `GET /admin/google/status` → `{"connected": bool, "email": str | null}`

- [ ] **Step 1: Write failing tests in `tests/test_admin_google_calendar.py`**

```python
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "$2b$12$placeholder")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-gcal-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-gcal-secret")

import jwt
import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import get_settings
from app.db import session_scope
from app.main import app
from app.models import StudioProfile

client = TestClient(app, follow_redirects=False)


def _auth() -> dict[str, str]:
    s = get_settings()
    token = jwt.encode(
        {"sub": s.admin_username, "exp": int(time.time()) + 3600},
        s.admin_jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _create_profile(**kwargs) -> None:
    with session_scope() as s:
        p = s.get(StudioProfile, 1)
        if p is None:
            p = StudioProfile(id=1, studio_name="Test")
            s.add(p)
        for k, v in kwargs.items():
            setattr(p, k, v)


def test_auth_url_requires_auth():
    resp = client.get("/admin/google/auth-url")
    assert resp.status_code == 403


def test_auth_url_returns_google_url():
    resp = client.get("/admin/google/auth-url", headers=_auth())
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert "accounts.google.com" in url
    assert "test-gcal-client-id" in url
    assert "calendar.events" in url


@respx.mock
def test_callback_stores_tokens_and_redirects():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(200, json={
            "access_token": "acc123",
            "refresh_token": "ref456",
            "expires_in": 3600,
        })
    )
    resp = client.get("/admin/google/callback?code=authcode123")
    assert resp.status_code in (302, 307)
    assert "/dashboard/" in resp.headers["location"]

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        assert profile.google_refresh_token == "ref456"
        assert profile.google_access_token == "acc123"


def test_disconnect_clears_tokens():
    _create_profile(
        google_access_token="acc",
        google_refresh_token="ref",
        google_token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    resp = client.delete("/admin/google/disconnect", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["disconnected"] is True

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        assert profile.google_refresh_token is None
        assert profile.google_access_token is None


def test_status_disconnected_when_no_profile():
    resp = client.get("/admin/google/status", headers=_auth())
    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "email": None}


@respx.mock
def test_status_connected_with_email():
    _create_profile(
        google_access_token="acc",
        google_refresh_token="ref",
        google_token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    respx.get("https://www.googleapis.com/oauth2/v3/userinfo").mock(
        return_value=Response(200, json={"email": "owner@gmail.com"})
    )
    resp = client.get("/admin/google/status", headers=_auth())
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["email"] == "owner@gmail.com"
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_admin_google_calendar.py -x -q
```
Expected: `404 Not Found` (routes not registered yet)

- [ ] **Step 3: Create `app/admin/google_calendar.py`**

```python
from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.admin.auth import require_admin_token
from app.admin.schemas import GoogleStatusOut
from app.config import get_settings
from app.db import session_scope
from app.models import StudioProfile

router = APIRouter(prefix="/admin/google", tags=["admin"])

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_SCOPES = "https://www.googleapis.com/auth/calendar.events"


@router.get("/auth-url")
def get_auth_url(auth: None = Depends(require_admin_token)) -> dict[str, str]:
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.admin_base_url}/admin/google/callback",
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return {"url": f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"}


@router.get("/callback")
def oauth_callback(code: str) -> RedirectResponse:
    settings = get_settings()
    resp = httpx.post(_TOKEN_URL, data={
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.admin_base_url}/admin/google/callback",
    })
    resp.raise_for_status()
    data = resp.json()
    now = datetime.now(timezone.utc)

    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if profile is None:
            profile = StudioProfile(id=1, studio_name="Hualienvibe")
            s.add(profile)
        profile.google_access_token = data["access_token"]
        if data.get("refresh_token"):
            profile.google_refresh_token = data["refresh_token"]
        profile.google_token_expiry = now + timedelta(seconds=data.get("expires_in", 3600))

    return RedirectResponse(url="/dashboard/")


@router.delete("/disconnect")
def disconnect(auth: None = Depends(require_admin_token)) -> dict[str, bool]:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if profile:
            profile.google_access_token = None
            profile.google_refresh_token = None
            profile.google_token_expiry = None
    return {"disconnected": True}


@router.get("/status", response_model=GoogleStatusOut)
def get_status(auth: None = Depends(require_admin_token)) -> GoogleStatusOut:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        if not profile or not profile.google_refresh_token:
            return GoogleStatusOut(connected=False)
        access_token = profile.google_access_token

    if not access_token:
        return GoogleStatusOut(connected=True)

    try:
        resp = httpx.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return GoogleStatusOut(connected=True, email=resp.json().get("email"))
    except Exception:
        pass

    return GoogleStatusOut(connected=True)
```

- [ ] **Step 4: Register router in `app/main.py`**

Add import at top with other admin router imports:
```python
from app.admin.google_calendar import router as admin_google_calendar_router
```

Add registration after `admin_schedule_router`:
```python
app.include_router(admin_google_calendar_router)
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
pytest tests/test_admin_google_calendar.py -x -q
```
Expected: 7 passed

- [ ] **Step 6: Run full suite**

```bash
pytest tests/ -x -q
```
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add app/admin/google_calendar.py app/main.py tests/test_admin_google_calendar.py
git commit -m "feat: add google calendar oauth admin endpoints"
```

---

## Task 4: Hook Into Booking and Cancellation

**Files:**
- Modify: `app/agent_tools.py`
- Modify: `app/admin/appointments.py`

**Interfaces:**
- Consumes: `create_event(...)`, `delete_event(...)` from `app.google_calendar`
- Consumes: `Appointment.google_calendar_event_id` (new column from Task 1)

- [ ] **Step 1: Hook `create_event` into `_book_appointment` in `app/agent_tools.py`**

In `_book_appointment`, after the `with session_scope()` block that creates the appointment (after `appt_id_str = str(appt.id)`), add before the `send_booking_confirmation` call:

```python
import contextlib
from app import google_calendar as gcal

with contextlib.suppress(Exception):
    event_id = gcal.create_event(
        service_name=svc_name,
        scheduled_at=scheduled_at,
        duration_min=svc.duration_min,
        customer_name=customer_name,
        notes=notes or "",
    )
    if event_id:
        with session_scope() as s:
            appt_obj = s.get(Appointment, uuid.UUID(appt_id_str))
            if appt_obj:
                appt_obj.google_calendar_event_id = event_id
```

Note: `svc.duration_min` is accessed after the session closes. Extract it before the session closes — add `svc_duration = svc.duration_min` inside the `with session_scope()` block where `svc_price` is extracted. Then use `svc_duration` in the `create_event` call.

The full variable extraction block inside the session should be:
```python
appt_id_str = str(appt.id)
svc_name = svc.name
svc_price = svc.price
svc_duration = svc.duration_min
```

- [ ] **Step 2: Hook `delete_event` into `_cancel_appointment` in `app/agent_tools.py`**

In `_cancel_appointment`, inside the `with session_scope()` block, extract the event ID before closing:
```python
event_id = appt.google_calendar_event_id  # add this line before appt.status = "cancelled"
appt.status = "cancelled"
```

After the session closes (after the `with session_scope()` block), add:
```python
import contextlib
from app import google_calendar as gcal

if event_id:
    with contextlib.suppress(Exception):
        gcal.delete_event(event_id)
```

- [ ] **Step 3: Hook `delete_event` into admin appointment update in `app/admin/appointments.py`**

In `update_appointment`, extract the event ID before updating status:
```python
appt = s.get(Appointment, appointment_id)
if appt is None:
    raise HTTPException(status_code=404, detail="Appointment not found")
service = s.get(Service, appt.service_id)
event_id = appt.google_calendar_event_id  # add this line
appt.status = body.status
```

After the `with session_scope()` block, add:
```python
import contextlib
from app import google_calendar as gcal

if body.status == "cancelled" and event_id:
    with contextlib.suppress(Exception):
        gcal.delete_event(event_id)
```

Add `event_id: str | None = None` as a local variable before the `with session_scope()` block so it's in scope for the block after.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -x -q
```
Expected: all pass (Google calls are no-ops in tests — no refresh token set)

- [ ] **Step 5: Commit**

```bash
git add app/agent_tools.py app/admin/appointments.py
git commit -m "feat: hook google calendar create/delete into booking and cancellation"
```

---

## Task 5: Admin UI — Google Calendar Section

**Files:**
- Modify: `frontend/admin/index.html`

- [ ] **Step 1: Add Alpine.js state for Google Calendar**

In the `adminApp()` function, find the studio data block:
```javascript
studio: {
  studio_name: '', ...
},
```

Add after `studioMsg: '',`:
```javascript
// ── Google Calendar ───────────────────────────────────────────────────
googleCal: { connected: false, email: null },
googleCalLoading: false,
googleCalMsg: '',

async loadGoogleCalStatus() {
  const res = await this.api('/admin/google/status');
  if (res.ok) this.googleCal = await res.json();
},
async connectGoogleCal() {
  const res = await this.api('/admin/google/auth-url');
  if (res.ok) {
    const { url } = await res.json();
    window.location.href = url;
  }
},
async disconnectGoogleCal() {
  this.googleCalLoading = true;
  await this.api('/admin/google/disconnect', { method: 'DELETE' });
  this.googleCal = { connected: false, email: null };
  this.googleCalMsg = 'Disconnected.';
  this.googleCalLoading = false;
  setTimeout(() => this.googleCalMsg = '', 3000);
},
```

- [ ] **Step 2: Call `loadGoogleCalStatus` on studio tab load**

Find `async loadStudio()` and add the status call at the end:
```javascript
async loadStudio() {
  const res = await this.api('/admin/studio');
  if (res.ok) this.studio = await res.json();
  await this.loadGoogleCalStatus();
},
```

- [ ] **Step 3: Add Google Calendar HTML section**

Inside `<!-- TAB:STUDIO:START -->`, after the closing `</div>` of the save button div (line 143, after `</div>` that closes the Studio Profile card), add before `<!-- TAB:STUDIO:END -->`:

```html
      <!-- Google Calendar -->
      <div class="bg-white rounded-2xl shadow-sm p-6 mt-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold text-[#241914]">Google Calendar</h2>
          <span x-show="googleCalMsg" x-text="googleCalMsg"
            class="text-sm text-green-600"></span>
        </div>
        <div x-show="!googleCal.connected">
          <p class="text-sm text-gray-500 mb-4">Connect your Google Calendar to automatically add bookings as events.</p>
          <button @click="connectGoogleCal()"
            class="bg-[#B86E78] text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-[#a5606a]">
            Connect Google Calendar
          </button>
        </div>
        <div x-show="googleCal.connected" class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-green-600 font-medium">✅ Connected</span>
            <span x-show="googleCal.email" x-text="'as ' + googleCal.email"
              class="text-sm text-gray-500"></span>
          </div>
          <button @click="disconnectGoogleCal()" :disabled="googleCalLoading"
            class="text-sm text-red-500 hover:underline disabled:opacity-50">
            <span x-show="!googleCalLoading">Disconnect</span>
            <span x-show="googleCalLoading">Disconnecting…</span>
          </button>
        </div>
      </div>
```

- [ ] **Step 4: Manual verification**

Start the app locally (or check Railway deploy) and:
1. Open admin dashboard → Studio Profile tab
2. Confirm Google Calendar section appears below the Save button
3. Confirm "Connect Google Calendar" button is visible when not connected

- [ ] **Step 5: Commit**

```bash
git add frontend/admin/index.html
git commit -m "feat: add google calendar connect/disconnect section to admin UI"
```

---

## Task 6: Run Migration + Final Integration

- [ ] **Step 1: Run migration on production DB**

```bash
DATABASE_URL="postgresql://postgres:gSrOHyrmZAMSuIJDLvoGfHevicaHOopo@metro.proxy.rlwy.net:26099/railway" .venv/bin/alembic upgrade head
```
Expected: `Running upgrade 0002 -> 0003, add google calendar columns`

- [ ] **Step 2: Set env vars in Railway**

In Railway dashboard → nail-bot service → Variables, add:
- `GOOGLE_CLIENT_ID` = your Google Cloud Console OAuth client ID
- `GOOGLE_CLIENT_SECRET` = your Google Cloud Console OAuth client secret
- `ADMIN_BASE_URL` = `https://nail-bot-production.up.railway.app`

(Google Cloud Console → APIs & Services → Credentials → Create OAuth 2.0 Client ID → Authorized redirect URIs: `https://nail-bot-production.up.railway.app/admin/google/callback`)

- [ ] **Step 3: Push to trigger Railway deploy**

```bash
git push origin master
```

- [ ] **Step 4: End-to-end test**

1. Open `https://nail-bot-production.up.railway.app/dashboard/`
2. Studio Profile tab → Google Calendar section shows "Connect Google Calendar"
3. Click connect → Google OAuth → authorize → redirects back to dashboard
4. Section now shows "✅ Connected as owner@gmail.com"
5. Book an appointment via LINE bot → check Google Calendar for the event
6. Cancel the appointment via bot → event disappears from calendar
7. Cancel an appointment via admin Appointments panel → event disappears
8. Click Disconnect → section reverts to "Connect" button
