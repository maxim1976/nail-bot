from __future__ import annotations

import uuid
import zoneinfo
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import Appointment, DateOverride, WeeklyTemplate

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def available_slots(
    target_date: date,
    service_id: uuid.UUID,
    *,
    duration_min: int,
    session: Session | None = None,
) -> list[datetime]:
    """Return sorted tz-aware slot start times (Asia/Taipei) that are not yet booked."""

    def _compute(s: Session) -> list[datetime]:
        dow = target_date.weekday()
        template = s.get(WeeklyTemplate, dow)
        if template is None or not template.is_active:
            return []

        start_time: time = template.start_time
        end_time: time = template.end_time
        slot_min: int = template.slot_duration_min

        override = s.get(DateOverride, target_date)
        if override is not None:
            if override.is_blocked:
                return []
            if override.custom_start:
                start_time = override.custom_start
            if override.custom_end:
                end_time = override.custom_end

        slots: list[datetime] = []
        current = datetime.combine(target_date, start_time, tzinfo=TZ)
        end_dt = datetime.combine(target_date, end_time, tzinfo=TZ)
        step = timedelta(minutes=slot_min)
        while current + timedelta(minutes=duration_min) <= end_dt:
            slots.append(current)
            current += step

        if not slots:
            return []

        day_start = datetime.combine(target_date, time.min, tzinfo=TZ)
        day_end = datetime.combine(target_date, time.max, tzinfo=TZ)
        booked = s.execute(
            select(Appointment.scheduled_at, Appointment.duration_min).where(
                and_(
                    Appointment.scheduled_at >= day_start,
                    Appointment.scheduled_at <= day_end,
                    Appointment.status.in_(["confirmed"]),
                )
            )
        ).all()

        booked_ranges = [
            (row.scheduled_at, row.scheduled_at + timedelta(minutes=row.duration_min))
            for row in booked
        ]

        def overlaps(slot_start: datetime) -> bool:
            slot_end = slot_start + timedelta(minutes=duration_min)
            return any(
                slot_start < b_end and slot_end > b_start
                for b_start, b_end in booked_ranges
            )

        return [s_dt for s_dt in slots if not overlaps(s_dt)]

    if session is not None:
        return _compute(session)
    with session_scope() as s:
        return _compute(s)
