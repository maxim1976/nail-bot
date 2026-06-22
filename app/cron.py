from __future__ import annotations

import zoneinfo
from datetime import datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.models import Appointment, Service, User

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
        template = _REMINDER_TEMPLATES.get(lang, _REMINDER_TEMPLATES["zh"])
        text = template.format(time=time_str, service=service_name)
        client.push(line_user_id=line_user_id, messages=[ReplyMessage.text(text)])
        with session_scope() as s:
            appt = s.get(Appointment, appt_id)
            if appt:
                appt.reminder_sent = True
                s.flush()


def send_morning_summary() -> None:
    pass  # implemented in Task 3
