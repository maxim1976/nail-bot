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
