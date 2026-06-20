from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.admin.schemas import LoginIn, TokenOut
from app.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])

_bearer = HTTPBearer(auto_error=False)

_TOKEN_EXPIRY_HOURS = 24


def require_admin_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if creds is None:
        raise HTTPException(status_code=403, detail="Missing authorization credentials")

    settings = get_settings()
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.admin_jwt_secret,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("sub") != settings.admin_username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn) -> TokenOut:
    settings = get_settings()
    if body.username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    stored_hash = settings.admin_password_hash
    if not stored_hash or not bcrypt.checkpw(body.password.encode(), stored_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode(
        {
            "sub": settings.admin_username,
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS),
        },
        settings.admin_jwt_secret,
        algorithm="HS256",
    )
    return TokenOut(access_token=token)


@router.get("/studio")
def get_studio(
    _: None = Depends(require_admin_token),
) -> dict[str, str]:
    # This is a placeholder for the studio admin endpoint
    # Actual implementation will be in a later task
    raise HTTPException(status_code=404, detail="Studio not found")
