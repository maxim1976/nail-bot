from __future__ import annotations

import zoneinfo
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.line_client import LineClient
    from app.models import Appointment, Service, User

TZ = zoneinfo.ZoneInfo("Asia/Taipei")

_CUSTOMER_TEMPLATES: dict[str, str] = {
    "zh": (
        "✅ 預約確認\n"
        "服務：{service}\n"
        "日期：{date}\n"
        "費用：NT${price}\n"
        "如需取消請提前告知，謝謝 🌸"
    ),
    "en": (
        "✅ Booking Confirmed\n"
        "Service: {service}\n"
        "Date: {date}\n"
        "Price: NT${price}\n"
        "Please notify us in advance to cancel. Thank you 🌸"
    ),
    "tl": (
        "✅ Nakumpirma ang Booking\n"
        "Serbisyo: {service}\n"
        "Petsa: {date}\n"
        "Presyo: NT${price}\n"
        "Mangyaring ipaalam nang maaga kung kailangan mong mag-cancel 🌸"
    ),
    "id": (
        "✅ Pemesanan Dikonfirmasi\n"
        "Layanan: {service}\n"
        "Tanggal: {date}\n"
        "Harga: NT${price}\n"
        "Harap beritahu kami jika perlu membatalkan 🌸"
    ),
    "vi": (
        "✅ Đặt Lịch Thành Công\n"
        "Dịch vụ: {service}\n"
        "Ngày: {date}\n"
        "Giá: NT${price}\n"
        "Vui lòng thông báo trước nếu cần hủy 🌸"
    ),
}

_OWNER_TEMPLATE = (
    "📅 新預約通知\n"
    "客戶：{customer}\n"
    "服務：{service}\n"
    "時間：{date}\n"
    "{notes}"
)


def _format_dt(dt: Any) -> str:
    local = dt.astimezone(TZ)
    return local.strftime("%Y/%m/%d %H:%M")


def send_booking_confirmation(
    *,
    appt: "Appointment",
    service: "Service",
    user: "User",
    line_client: "LineClient",
    owner_line_user_id: str | None,
) -> None:
    from app.line_client import ReplyMessage

    lang = (user.preferred_language or "zh") if hasattr(user, "preferred_language") else "zh"
    template = _CUSTOMER_TEMPLATES.get(lang, _CUSTOMER_TEMPLATES["zh"])
    customer_text = template.format(
        service=service.name,
        date=_format_dt(appt.scheduled_at),
        price=service.price,
    )
    line_client.push(
        line_user_id=appt.line_user_id,
        messages=[ReplyMessage.text(customer_text)],
    )

    if owner_line_user_id:
        notes_str = f"備註：{appt.notes}" if appt.notes else ""
        owner_text = _OWNER_TEMPLATE.format(
            customer=appt.customer_name,
            service=service.name,
            date=_format_dt(appt.scheduled_at),
            notes=notes_str,
        )
        line_client.push(
            line_user_id=owner_line_user_id,
            messages=[ReplyMessage.text(owner_text)],
        )
