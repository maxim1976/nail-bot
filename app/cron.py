from __future__ import annotations

import logging
import zoneinfo
from datetime import datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.models import Appointment, Service, User

logger = logging.getLogger(__name__)

_TZ = zoneinfo.ZoneInfo("Asia/Taipei")

_REMINDER_TEMPLATES: dict[str, str] = {
    "zh": "⏰ 預約提醒\n明天 {time} 您有預約 {service}，期待為您服務！🌸",
    "en": "⏰ Reminder: Your nail appointment is tomorrow at {time} for {service}. See you soon! 🌸",
    "tl": "⏰ Paalala: Mayroon kang appointment bukas ng {time} para sa {service}. Hanggang bukas! 🌸",
    "id": "⏰ Pengingat: Anda memiliki janji kecantikan kuku besok pukul {time} untuk {service}. Sampai jumpa! 🌸",
    "vi": "⏰ Nhắc nhở: Bạn có lịch làm móng vào ngày mai lúc {time} cho {service}. Hẹn gặp! 🌸",
}


def send_24h_reminders() -> None:
    settings = get_settings()
    now = datetime.now(_TZ)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)

    with session_scope() as s:
        rows = s.execute(
            select(Appointment, Service, User)
            .join(Service, Appointment.service_id == Service.id)
            .join(User, Appointment.line_user_id == User.line_user_id)
            .where(
                Appointment.scheduled_at >= window_start,
                Appointment.scheduled_at < window_end,
                Appointment.status == "confirmed",
                Appointment.reminder_sent == False,  # noqa: E712
            )
            .order_by(Appointment.scheduled_at)
        ).all()

        to_send = [
            (
                appt.id,
                appt.line_user_id,
                appt.scheduled_at.astimezone(_TZ).strftime("%H:%M"),
                service.name,
                user.preferred_language or "zh",
            )
            for appt, service, user in rows
        ]

    if not to_send:
        return

    client = LineClient(channel_access_token=settings.line_channel_access_token)
    for appt_id, line_user_id, time_str, service_name, lang in to_send:
        try:
            template = _REMINDER_TEMPLATES.get(lang, _REMINDER_TEMPLATES["zh"])
            text = template.format(time=time_str, service=service_name)
            client.push(line_user_id=line_user_id, messages=[ReplyMessage.text(text)])
            with session_scope() as s:
                appt = s.get(Appointment, appt_id)
                if appt:
                    appt.reminder_sent = True
        except Exception:
            logger.exception(
                "Failed to send reminder for appointment %s", appt_id
            )


def send_morning_summary() -> None:
    settings = get_settings()
    if not settings.owner_line_user_id:
        return

    now = datetime.now(_TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)  # day_end exclusive — use < comparison

    with session_scope() as s:
        rows = s.execute(
            select(Appointment, Service)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.scheduled_at >= day_start,
                Appointment.scheduled_at < day_end,
                Appointment.status == "confirmed",
            )
            .order_by(Appointment.scheduled_at)
        ).all()

        appts_data = [
            (
                appt.scheduled_at.astimezone(_TZ).strftime("%H:%M"),
                appt.customer_name,
                service.name,
            )
            for appt, service in rows
        ]

    if not appts_data:
        text = "📋 今日無預約"
    else:
        lines = [f"📋 今日預約（{len(appts_data)} 筆）"]
        for time_str, customer_name, service_name in appts_data:
            lines.append(f"• {time_str}  {customer_name} — {service_name}")
        text = "\n".join(lines)

    client = LineClient(channel_access_token=settings.line_channel_access_token)
    client.push(
        line_user_id=settings.owner_line_user_id,
        messages=[ReplyMessage.text(text)],
    )
