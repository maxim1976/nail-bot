# Google Calendar Integration — Design Spec

**Date:** 2026-06-25
**Status:** Approved

## Overview

Automatically sync nail studio appointments to the owner's Google Calendar. Every booking creates a calendar event; every cancellation deletes it. The owner connects their Google account once via OAuth in the admin dashboard — fully automatic after that.

---

## Data Model

### `StudioProfile` — three new columns

| Column | Type | Notes |
|---|---|---|
| `google_access_token` | `String`, nullable | Short-lived OAuth access token |
| `google_refresh_token` | `String`, nullable | Long-lived refresh token; persists across access token expiry |
| `google_token_expiry` | `DateTime(timezone=True)`, nullable | When the access token expires |

### `Appointment` — one new column

| Column | Type | Notes |
|---|---|---|
| `google_calendar_event_id` | `String`, nullable | Google Calendar event ID; stored after creation so we can delete it later |

### Alembic migration

Single migration (`0003_google_calendar.py`) adding all four columns.

### Environment variables

| Variable | Purpose |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |

---

## Backend

### New module: `app/google_calendar.py`

Responsibilities:
- `_get_credentials()` — loads tokens from `StudioProfile` row 1; calls Google token refresh endpoint if `google_token_expiry` is past; saves updated access token back to DB
- `create_event(appt, service) -> str | None` — builds a Google Calendar event (title = service name, start/end from `scheduled_at` + `duration_min`, description includes customer name and notes), calls Calendar API, returns event ID
- `delete_event(event_id) -> None` — deletes the event by ID; silently ignores 404 (already deleted)
- `is_connected() -> bool` — returns True if `google_refresh_token` is set on StudioProfile

If Google is not connected (`is_connected()` returns False), `create_event` and `delete_event` are no-ops.

### New admin endpoints: `app/admin/google_calendar.py`

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/google/auth-url` | Returns the Google OAuth authorization URL with scopes `calendar.events` |
| `GET` | `/admin/google/callback` | Receives `code` from Google, exchanges for tokens, stores in `StudioProfile`, redirects to admin dashboard |
| `DELETE` | `/admin/google/disconnect` | Clears all three token columns on `StudioProfile` |
| `GET` | `/admin/google/status` | Returns `{ connected: bool, email: str | null }` |

OAuth redirect URI: `{admin_base_url}/admin/google/callback`

### Hooks into existing code

**`app/agent_tools.py` — `_book_appointment`**
After saving the appointment and flushing, call `create_event(appt, svc)` and store the returned event ID on `appt.google_calendar_event_id`. Wrapped in `contextlib.suppress(Exception)` so a Google failure never breaks booking.

**`app/agent_tools.py` — `_cancel_appointment`**
After setting `appt.status = "cancelled"`, call `delete_event(appt.google_calendar_event_id)` if the ID is set. Wrapped in `contextlib.suppress(Exception)`.

**`app/admin/appointments.py` — status update endpoint**
Same pattern: when status is set to `"cancelled"`, call `delete_event` on the event ID if present.

---

## Admin UI (`frontend/admin/index.html`)

New section below Studio Profile, always visible. Two states:

**Disconnected:**
```
[ Google Calendar ]
─────────────────────────────
Connect your Google Calendar to automatically add bookings as events.

  [ Connect Google Calendar ]          ← button, links to /admin/google/auth-url
```

**Connected:**
```
[ Google Calendar ]
─────────────────────────────
✅ Connected as: owner@gmail.com

  [ Disconnect ]                        ← DELETE /admin/google/disconnect
```

The section loads its state from `GET /admin/google/status` on page load (same pattern as Studio Profile data fetch).

---

## Token Refresh

No cron or background task needed. `_get_credentials()` checks `google_token_expiry` before every API call. If expired (or within 60 seconds of expiry), it calls Google's token refresh endpoint synchronously, updates `StudioProfile`, and returns fresh credentials. Google refresh tokens do not expire unless manually revoked.

---

## Error Handling

- Google API failures on booking/cancel are suppressed — LINE notification still goes through
- If `google_refresh_token` is missing or revoked, `is_connected()` returns False and all calendar calls are skipped
- Admin status endpoint surfaces disconnected state so owner knows to reconnect

---

## Verification

1. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Railway env vars
2. In admin dashboard, click "Connect Google Calendar" → complete OAuth → status shows connected email
3. Book an appointment via LINE bot → event appears in Google Calendar
4. Cancel the appointment via bot → event disappears from Google Calendar
5. Cancel via admin panel → event disappears
6. Disconnect from admin → status shows disconnected; new bookings create no calendar events
