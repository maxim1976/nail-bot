from __future__ import annotations

import contextlib
import json
import uuid
import zoneinfo
from datetime import datetime

from sqlalchemy import select

from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.models import Appointment, Service, User
from app.slots import available_slots

TZ = zoneinfo.ZoneInfo("Asia/Taipei")

BOOKING_TOOLS: list[dict] = [
    {
        "name": "book_appointment",
        "description": (
            "Book an appointment for the customer. "
            "Call get_services first to get service_id, call get_available_slots to confirm "
            "the time is open, collect the customer's name, then call this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {
                    "type": "string",
                    "description": "UUID of the service (from get_services)",
                },
                "scheduled_at": {
                    "type": "string",
                    "description": "Datetime in 'YYYY-MM-DD HH:MM' format, Asia/Taipei timezone",
                },
                "customer_name": {
                    "type": "string",
                    "description": "Customer's name",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional special requests or notes",
                },
            },
            "required": ["service_id", "scheduled_at", "customer_name"],
        },
    },
    {
        "name": "get_my_appointments",
        "description": "Retrieve the customer's upcoming confirmed appointments.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "cancel_appointment",
        "description": (
            "Cancel one of the customer's confirmed appointments by its ID "
            "and send them a LINE cancellation notification."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "UUID of the appointment to cancel (obtain from get_my_appointments)",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "name": "get_services",
        "description": "List all available nail services with their duration and price.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_available_slots",
        "description": "Get available booking time slots for a given date (Asia/Taipei timezone).",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Target date in YYYY-MM-DD format",
                },
                "service_id": {
                    "type": "string",
                    "description": "Optional service UUID — uses the service's duration_min for slot calculation",
                },
            },
            "required": ["date"],
        },
    },
]


def _get_my_appointments(line_user_id: str) -> str:
    with session_scope() as s:
        rows = s.execute(
            select(
                Appointment.id,
                Appointment.scheduled_at,
                Appointment.duration_min,
                Service.name.label("service_name"),
            )
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.line_user_id == line_user_id,
                Appointment.status == "confirmed",
                Appointment.scheduled_at >= datetime.now(tz=TZ),
            )
            .order_by(Appointment.scheduled_at)
        ).all()
        result = [
            {
                "id": str(r.id),
                "service": r.service_name,
                "scheduled_at": r.scheduled_at.astimezone(TZ).strftime("%Y-%m-%d %H:%M"),
                "duration_min": r.duration_min,
            }
            for r in rows
        ]
    if not result:
        return json.dumps({"appointments": [], "message": "No upcoming appointments found."})
    return json.dumps({"appointments": result})


def _cancel_appointment(appointment_id: str, *, line_user_id: str) -> str:
    try:
        appt_uuid = uuid.UUID(appointment_id)
    except ValueError:
        return json.dumps({"error": "Invalid appointment ID format."})

    svc_name = ""
    scheduled_str = ""
    cal_event_id: str | None = None
    with session_scope() as s:
        appt = s.get(Appointment, appt_uuid)
        if appt is None or appt.line_user_id != line_user_id:
            return json.dumps({"error": "Appointment not found."})
        if appt.status != "confirmed":
            return json.dumps({"error": f"Cannot cancel appointment with status '{appt.status}'."})
        svc = s.get(Service, appt.service_id) if appt.service_id else None
        svc_name = svc.name if svc else ""
        scheduled_str = appt.scheduled_at.astimezone(TZ).strftime("%Y/%m/%d %H:%M")
        cal_event_id = appt.google_calendar_event_id
        appt.status = "cancelled"

    from app.config import get_settings

    lc = LineClient(channel_access_token=get_settings().line_channel_access_token)
    msg = f"❌ 已取消預約\n服務：{svc_name}\n時間：{scheduled_str}"
    try:
        lc.push(line_user_id=line_user_id, messages=[ReplyMessage.text(msg)])
    except Exception:
        pass

    if cal_event_id:
        from app import google_calendar as gcal
        with contextlib.suppress(Exception):
            gcal.delete_event(cal_event_id)

    return json.dumps({"success": True, "service": svc_name, "cancelled_at": scheduled_str})


def _get_services() -> str:
    with session_scope() as s:
        rows = s.execute(
            select(
                Service.id,
                Service.name,
                Service.name_en,
                Service.duration_min,
                Service.price,
                Service.category,
            )
            .where(Service.is_available == True)  # noqa: E712
            .order_by(Service.sort_order)
        ).all()
        result = [
            {
                "id": str(r.id),
                "name": r.name,
                "name_en": r.name_en,
                "duration_min": r.duration_min,
                "price": r.price,
                "category": r.category,
            }
            for r in rows
        ]
    return json.dumps({"services": result})


def _book_appointment(
    service_id: str,
    scheduled_at_str: str,
    customer_name: str,
    notes: str | None,
    *,
    line_user_id: str,
) -> str:
    try:
        svc_uuid = uuid.UUID(service_id)
    except ValueError:
        return json.dumps({"error": "Invalid service_id format."})

    scheduled_at: datetime | None = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            scheduled_at = datetime.strptime(scheduled_at_str, fmt).replace(tzinfo=TZ)
            break
        except ValueError:
            continue
    if scheduled_at is None:
        return json.dumps({"error": "Invalid scheduled_at format. Use YYYY-MM-DD HH:MM."})

    svc_name = ""
    svc_price: int | float = 0
    user_lang = "zh"
    appt_id_str = ""

    with session_scope() as s:
        svc = s.get(Service, svc_uuid)
        if svc is None:
            return json.dumps({"error": "Service not found."})

        open_slots = available_slots(
            target_date=scheduled_at.date(),
            service_id=svc_uuid,
            duration_min=svc.duration_min,
            session=s,
        )
        if scheduled_at not in open_slots:
            return json.dumps({"error": "That slot is no longer available. Please choose another time."})

        user = s.get(User, line_user_id)
        if user is None:
            user = User(line_user_id=line_user_id)
            s.add(user)
            s.flush()
        user_lang = user.preferred_language or "zh"

        appt = Appointment(
            line_user_id=line_user_id,
            service_id=svc_uuid,
            scheduled_at=scheduled_at,
            duration_min=svc.duration_min,
            customer_name=customer_name,
            notes=notes or "",
            status="confirmed",
        )
        s.add(appt)
        s.flush()

        appt_id_str = str(appt.id)
        svc_name = svc.name
        svc_price = svc.price
        svc_duration = svc.duration_min

    from types import SimpleNamespace

    from app.config import get_settings
    from app.notifications import send_booking_confirmation

    settings = get_settings()
    lc = LineClient(channel_access_token=settings.line_channel_access_token)
    with contextlib.suppress(Exception):
        send_booking_confirmation(
            appt=SimpleNamespace(
                line_user_id=line_user_id,
                scheduled_at=scheduled_at,
                customer_name=customer_name,
                notes=notes or "",
            ),
            service=SimpleNamespace(name=svc_name, price=svc_price),
            user=SimpleNamespace(preferred_language=user_lang),
            line_client=lc,
            owner_line_user_id=settings.owner_line_user_id,
        )

    from app import google_calendar as gcal
    with contextlib.suppress(Exception):
        event_id = gcal.create_event(
            service_name=svc_name,
            scheduled_at=scheduled_at,
            duration_min=svc_duration,
            customer_name=customer_name,
            notes=notes or "",
        )
        if event_id:
            with session_scope() as s:
                appt_obj = s.get(Appointment, uuid.UUID(appt_id_str))
                if appt_obj:
                    appt_obj.google_calendar_event_id = event_id

    return json.dumps({
        "success": True,
        "appointment_id": appt_id_str,
        "service": svc_name,
        "scheduled_at": scheduled_at.strftime("%Y/%m/%d %H:%M"),
        "customer_name": customer_name,
    })


def _get_available_slots(date_str: str, service_id: str | None = None) -> str:
    from datetime import date as date_t

    try:
        target_date = date_t.fromisoformat(date_str)
    except ValueError:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    duration_min = 60
    svc_uuid: uuid.UUID | None = None
    if service_id:
        try:
            svc_uuid = uuid.UUID(service_id)
        except ValueError:
            return json.dumps({"error": "Invalid service_id format."})
        with session_scope() as s:
            svc = s.get(Service, svc_uuid)
            if svc:
                duration_min = svc.duration_min

    slots = available_slots(target_date, svc_uuid, duration_min=duration_min)
    slot_strs = [dt.astimezone(TZ).strftime("%H:%M") for dt in slots]
    return json.dumps({"date": date_str, "slots": slot_strs})


def execute_tool(name: str, tool_input: dict, *, line_user_id: str) -> str:
    if name == "book_appointment":
        svc_id = tool_input.get("service_id")
        sched = tool_input.get("scheduled_at")
        cname = tool_input.get("customer_name")
        if not svc_id or not sched or not cname:
            return json.dumps({"error": "missing required fields: service_id, scheduled_at, customer_name"})
        return _book_appointment(svc_id, sched, cname, tool_input.get("notes"), line_user_id=line_user_id)
    if name == "get_my_appointments":
        return _get_my_appointments(line_user_id)
    if name == "cancel_appointment":
        appt_id = tool_input.get("appointment_id")
        if not appt_id:
            return json.dumps({"error": "missing required field: appointment_id"})
        return _cancel_appointment(appt_id, line_user_id=line_user_id)
    if name == "get_services":
        return _get_services()
    if name == "get_available_slots":
        date_str = tool_input.get("date")
        if not date_str:
            return json.dumps({"error": "missing required field: date"})
        return _get_available_slots(date_str, tool_input.get("service_id"))
    return json.dumps({"error": f"Unknown tool: {name!r}"})
