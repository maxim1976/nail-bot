from __future__ import annotations

import uuid
import zoneinfo
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.schemas import AppointmentIn, AppointmentOut, SlotOut
from app.db import session_scope
from app.models import Appointment, Service, User
from app.slots import available_slots

router = APIRouter(prefix="/api", tags=["public"])

TZ = zoneinfo.ZoneInfo("Asia/Taipei")


@router.get("/slots", response_model=list[SlotOut])
def get_slots(service_id: uuid.UUID, date: date) -> list[SlotOut]:
    with session_scope() as s:
        service = s.get(Service, service_id)
        if service is None:
            raise HTTPException(status_code=404, detail="Service not found")
        slots = available_slots(target_date=date, service_id=service_id,
                                duration_min=service.duration_min, session=s)
    return [SlotOut(start=dt) for dt in slots]


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(body: AppointmentIn) -> AppointmentOut:
    with session_scope() as s:
        service = s.get(Service, body.service_id)
        if service is None:
            raise HTTPException(status_code=404, detail="Service not found")

        # Normalize FIRST, then use normalized date for slot lookup
        scheduled_at = body.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=TZ)
        else:
            scheduled_at = scheduled_at.astimezone(TZ)

        available = available_slots(
            target_date=scheduled_at.date(),
            service_id=body.service_id,
            duration_min=service.duration_min,
            session=s,
        )

        if scheduled_at not in available:
            raise HTTPException(status_code=409, detail="Slot no longer available")

        user = s.get(User, body.line_user_id)
        if user is None:
            user = User(line_user_id=body.line_user_id)
            s.add(user)
            s.flush()

        appt = Appointment(
            line_user_id=body.line_user_id,
            service_id=body.service_id,
            scheduled_at=scheduled_at,
            duration_min=service.duration_min,
            customer_name=body.customer_name,
            notes=body.notes,
            status="confirmed",
        )
        s.add(appt)
        s.flush()

        return AppointmentOut(
            id=appt.id,
            service_name=service.name,
            scheduled_at=appt.scheduled_at,
            duration_min=appt.duration_min,
            status=appt.status,
            customer_name=appt.customer_name,
            notes=appt.notes,
        )


@router.get("/my-appointments", response_model=list[AppointmentOut])
def my_appointments(line_user_id: str = Query(...)) -> list[AppointmentOut]:
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        rows = (
            s.execute(
                select(Appointment, Service)
                .join(Service, Appointment.service_id == Service.id)
                .where(
                    Appointment.line_user_id == line_user_id,
                    Appointment.scheduled_at >= now,
                    Appointment.status == "confirmed",
                )
                .order_by(Appointment.scheduled_at)
            )
            .all()
        )
    return [
        AppointmentOut(
            id=appt.id,
            service_name=svc.name,
            scheduled_at=appt.scheduled_at,
            duration_min=appt.duration_min,
            status=appt.status,
            customer_name=appt.customer_name,
            notes=appt.notes,
        )
        for appt, svc in rows
    ]
