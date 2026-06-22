from __future__ import annotations

import uuid
import zoneinfo
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.admin.auth import require_admin_token
from app.admin.schemas import AdminAppointmentOut, AdminAppointmentUpdate
from app.db import session_scope
from app.models import Appointment, Service

router = APIRouter(prefix="/admin", tags=["admin"])

_TZ = zoneinfo.ZoneInfo("Asia/Taipei")


@router.get("/appointments", response_model=list[AdminAppointmentOut])
def list_appointments(
    status: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    auth: None = Depends(require_admin_token),
) -> list[AdminAppointmentOut]:
    with session_scope() as s:
        q = (
            select(Appointment, Service.name.label("service_name"))
            .join(Service, Appointment.service_id == Service.id)
            .order_by(Appointment.scheduled_at)
        )
        if status:
            q = q.where(Appointment.status == status)
        if from_date:
            q = q.where(Appointment.scheduled_at >= datetime.combine(from_date, time.min, tzinfo=_TZ))
        if to_date:
            end_dt = datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=_TZ)
            q = q.where(Appointment.scheduled_at < end_dt)
        rows = s.execute(q).all()
        return [
            AdminAppointmentOut(
                id=appt.id,
                line_user_id=appt.line_user_id,
                service_name=service_name,
                scheduled_at=appt.scheduled_at,
                duration_min=appt.duration_min,
                status=appt.status,
                customer_name=appt.customer_name,
                notes=appt.notes,
            )
            for appt, service_name in rows
        ]


@router.put("/appointments/{appointment_id}", response_model=AdminAppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    body: AdminAppointmentUpdate,
    auth: None = Depends(require_admin_token),
) -> AdminAppointmentOut:
    with session_scope() as s:
        appt = s.get(Appointment, appointment_id)
        if appt is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
        service = s.get(Service, appt.service_id)
        appt.status = body.status
        s.flush()
        return AdminAppointmentOut(
            id=appt.id,
            line_user_id=appt.line_user_id,
            service_name=service.name if service else "",
            scheduled_at=appt.scheduled_at,
            duration_min=appt.duration_min,
            status=appt.status,
            customer_name=appt.customer_name,
            notes=appt.notes,
        )
