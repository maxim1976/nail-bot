from __future__ import annotations

import json
import uuid
import zoneinfo
from datetime import datetime

from sqlalchemy import select

from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.models import Appointment, Service

TZ = zoneinfo.ZoneInfo("Asia/Taipei")

BOOKING_TOOLS: list[dict] = [
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
    with session_scope() as s:
        appt = s.get(Appointment, appt_uuid)
        if appt is None or appt.line_user_id != line_user_id:
            return json.dumps({"error": "Appointment not found."})
        if appt.status != "confirmed":
            return json.dumps({"error": f"Cannot cancel appointment with status '{appt.status}'."})
        svc = s.get(Service, appt.service_id) if appt.service_id else None
        svc_name = svc.name if svc else ""
        scheduled_str = appt.scheduled_at.astimezone(TZ).strftime("%Y/%m/%d %H:%M")
        appt.status = "cancelled"

    from app.config import get_settings

    lc = LineClient(channel_access_token=get_settings().line_channel_access_token)
    msg = f"❌ 已取消預約\n服務：{svc_name}\n時間：{scheduled_str}"
    try:
        lc.push(line_user_id=line_user_id, messages=[ReplyMessage.text(msg)])
    except Exception:
        pass

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


def _get_available_slots(date_str: str, service_id: str | None = None) -> str:
    from datetime import date as date_t

    from app.slots import available_slots

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
    if name == "get_my_appointments":
        return _get_my_appointments(line_user_id)
    if name == "cancel_appointment":
        return _cancel_appointment(tool_input["appointment_id"], line_user_id=line_user_id)
    if name == "get_services":
        return _get_services()
    if name == "get_available_slots":
        return _get_available_slots(tool_input["date"], tool_input.get("service_id"))
    return json.dumps({"error": f"Unknown tool: {name!r}"})
