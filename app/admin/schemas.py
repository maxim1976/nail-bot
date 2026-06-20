from __future__ import annotations

import uuid
from datetime import date as dt_date, datetime, time

from pydantic import BaseModel, ConfigDict


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StudioProfileIn(BaseModel):
    studio_name: str
    owner_name: str | None = None
    address: str | None = None
    phone: str | None = None
    instagram: str | None = None
    cancellation_policy: str | None = None
    aftercare_notes: str | None = None
    ai_persona_notes: str | None = None
    owner_line_user_id: str | None = None


class StudioProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    studio_name: str
    owner_name: str | None
    address: str | None
    phone: str | None
    instagram: str | None
    cancellation_policy: str | None
    aftercare_notes: str | None
    ai_persona_notes: str | None
    owner_line_user_id: str | None
