from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select

from app.admin.auth import require_admin_token
from app.admin.schemas import (
    DateOverrideIn,
    DateOverrideOut,
    WeeklyTemplateIn,
    WeeklyTemplateOut,
)
from app.db import session_scope
from app.models import DateOverride, WeeklyTemplate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/weekly-template", response_model=list[WeeklyTemplateOut])
def list_weekly_template(auth: None = Depends(require_admin_token)) -> list[WeeklyTemplateOut]:
    with session_scope() as s:
        rows = s.execute(select(WeeklyTemplate).order_by(WeeklyTemplate.dow)).scalars().all()
        return [WeeklyTemplateOut.model_validate(r) for r in rows]


@router.put("/weekly-template/{dow}", response_model=WeeklyTemplateOut)
def put_weekly_template(
    dow: Annotated[int, Path(ge=0, le=6)],
    body: WeeklyTemplateIn,
    auth: None = Depends(require_admin_token),
) -> WeeklyTemplateOut:
    with session_scope() as s:
        row = s.get(WeeklyTemplate, dow)
        if row is None:
            row = WeeklyTemplate(dow=dow)
            s.add(row)
        row.start_time = body.start_time
        row.end_time = body.end_time
        row.slot_duration_min = body.slot_duration_min
        row.is_active = body.is_active
        s.flush()
        return WeeklyTemplateOut.model_validate(row)


@router.get("/date-overrides", response_model=list[DateOverrideOut])
def list_date_overrides(auth: None = Depends(require_admin_token)) -> list[DateOverrideOut]:
    with session_scope() as s:
        rows = s.execute(select(DateOverride).order_by(DateOverride.date)).scalars().all()
        return [DateOverrideOut.model_validate(r) for r in rows]


@router.post("/date-overrides", response_model=DateOverrideOut, status_code=201)
def upsert_date_override(
    body: DateOverrideIn,
    auth: None = Depends(require_admin_token),
) -> DateOverrideOut:
    with session_scope() as s:
        row = s.get(DateOverride, body.date)
        if row is None:
            row = DateOverride(date=body.date)
            s.add(row)
        row.is_blocked = body.is_blocked
        row.custom_start = body.custom_start
        row.custom_end = body.custom_end
        s.flush()
        return DateOverrideOut.model_validate(row)


@router.delete("/date-overrides/{override_date}", status_code=204)
def delete_date_override(
    override_date: date,
    auth: None = Depends(require_admin_token),
) -> None:
    with session_scope() as s:
        row = s.get(DateOverride, override_date)
        if row is None:
            raise HTTPException(status_code=404, detail="Date override not found")
        s.delete(row)
