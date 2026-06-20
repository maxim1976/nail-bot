from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    name_en: str
    name_tl: str
    name_id: str
    name_vi: str
    description: str
    duration_min: int
    price: int
    image_url: str | None
    category: str
    sort_order: int


class SlotOut(BaseModel):
    start: datetime


class AppointmentIn(BaseModel):
    line_user_id: str
    service_id: uuid.UUID
    scheduled_at: datetime
    customer_name: str
    notes: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    service_name: str
    scheduled_at: datetime
    duration_min: int
    status: str
    customer_name: str
    notes: str | None
