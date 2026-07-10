from __future__ import annotations

import contextlib
import json
import uuid
from datetime import date

from sqlalchemy import select

from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.lodging_pricing import QuoteError, quote_stay
from app.lodging_slots import available_units, is_available
from app.models import Booking, RoomType, User

LODGING_TOOLS: list[dict] = [
    {
        "name": "get_room_types",
        "description": "List all bookable room types (房型) with capacity and the three day-type prices (平日/旺日/連續假日).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "quote_stay",
        "description": (
            "Compute an itemised price quote for a stay. This is the tool to answer "
            "'多少錢'. Always call it instead of guessing prices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "room_type_id": {
                    "type": "string",
                    "description": "UUID of the room type (from get_room_types)",
                },
                "check_in": {
                    "type": "string",
                    "description": "Check-in date (first night) in YYYY-MM-DD format",
                },
                "check_out": {
                    "type": "string",
                    "description": "Check-out date (checkout morning) in YYYY-MM-DD format",
                },
                "guests": {
                    "type": "integer",
                    "description": "Number of guests (2歲以下嬰兒不計)",
                },
                "extra_beds": {
                    "type": "integer",
                    "description": "Number of extra beds requested (optional, default 0)",
                },
            },
            "required": ["room_type_id", "check_in", "check_out", "guests"],
        },
    },
    {
        "name": "check_availability",
        "description": "Check which room types are free for a given date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                "guests": {
                    "type": "integer",
                    "description": "Optional: only return room types that fit this many guests",
                },
            },
            "required": ["check_in", "check_out"],
        },
    },
    {
        "name": "book_stay",
        "description": (
            "Book a stay for the customer. Re-checks availability, computes the total, "
            "creates a confirmed booking and sends a LINE confirmation automatically. "
            "Confirm dates, guests and the customer's name before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "room_type_id": {"type": "string", "description": "UUID of the room type"},
                "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                "guests": {"type": "integer", "description": "Number of guests"},
                "customer_name": {"type": "string", "description": "Customer's name"},
                "extra_beds": {"type": "integer", "description": "Extra beds (optional, default 0)"},
                "notes": {"type": "string", "description": "Optional special requests"},
            },
            "required": ["room_type_id", "check_in", "check_out", "guests", "customer_name"],
        },
    },
    {
        "name": "get_my_bookings",
        "description": "Retrieve the customer's upcoming confirmed bookings.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "cancel_booking",
        "description": (
            "Cancel one of the customer's confirmed bookings by its ID and send a "
            "LINE cancellation notification."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "UUID of the booking (from get_my_bookings)",
                },
            },
            "required": ["booking_id"],
        },
    },
]


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _get_room_types() -> str:
    with session_scope() as s:
        rows = (
            s.execute(
                select(RoomType)
                .where(RoomType.is_available == True)  # noqa: E712
                .order_by(RoomType.sort_order)
            )
            .scalars()
            .all()
        )
        result = [
            {
                "id": str(r.id),
                "name": r.name,
                "name_en": r.name_en,
                "capacity": r.capacity,
                "max_capacity": r.max_capacity,
                "price_weekday": r.price_weekday,
                "price_peak": r.price_peak,
                "price_holiday": r.price_holiday,
                "extra_bed_price": r.extra_bed_price,
                "max_extra_beds": r.max_extra_beds,
            }
            for r in rows
        ]
    return json.dumps({"room_types": result}, ensure_ascii=False)


def _quote_stay(
    room_type_id: str,
    check_in_str: str,
    check_out_str: str,
    guests: int,
    extra_beds: int,
) -> str:
    try:
        rt_uuid = uuid.UUID(room_type_id)
    except (ValueError, TypeError):
        return json.dumps({"error": "Invalid room_type_id format."})
    check_in = _parse_date(check_in_str)
    check_out = _parse_date(check_out_str)
    if check_in is None or check_out is None:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    with session_scope() as s:
        room = s.get(RoomType, rt_uuid)
        if room is None:
            return json.dumps({"error": "Room type not found."})
        try:
            quote = quote_stay(room, check_in, check_out, guests, extra_beds, session=s)
        except QuoteError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps(quote, ensure_ascii=False)


def _check_availability(
    check_in_str: str, check_out_str: str, guests: int | None
) -> str:
    check_in = _parse_date(check_in_str)
    check_out = _parse_date(check_out_str)
    if check_in is None or check_out is None:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})
    if check_out <= check_in:
        return json.dumps({"error": "check_out must be after check_in."})

    with session_scope() as s:
        rows = (
            s.execute(
                select(RoomType)
                .where(RoomType.is_available == True)  # noqa: E712
                .order_by(RoomType.sort_order)
            )
            .scalars()
            .all()
        )
        available = []
        for room in rows:
            if guests is not None and guests > room.max_capacity:
                continue
            units = available_units(room.id, check_in, check_out, session=s)
            if units > 0:
                available.append(
                    {
                        "id": str(room.id),
                        "name": room.name,
                        "capacity": room.capacity,
                        "max_capacity": room.max_capacity,
                        "units_available": units,
                    }
                )
    return json.dumps(
        {"check_in": check_in_str, "check_out": check_out_str, "available": available},
        ensure_ascii=False,
    )


def _book_stay(
    room_type_id: str,
    check_in_str: str,
    check_out_str: str,
    guests: int,
    customer_name: str,
    extra_beds: int,
    notes: str | None,
    *,
    line_user_id: str,
) -> str:
    try:
        rt_uuid = uuid.UUID(room_type_id)
    except (ValueError, TypeError):
        return json.dumps({"error": "Invalid room_type_id format."})
    check_in = _parse_date(check_in_str)
    check_out = _parse_date(check_out_str)
    if check_in is None or check_out is None:
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    room_name = ""
    total_price = 0
    nights = 0
    user_lang = "zh"
    booking_id_str = ""

    with session_scope() as s:
        room = s.get(RoomType, rt_uuid)
        if room is None:
            return json.dumps({"error": "Room type not found."})

        try:
            quote = quote_stay(room, check_in, check_out, guests, extra_beds, session=s)
        except QuoteError as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

        if not is_available(rt_uuid, check_in, check_out, session=s):
            return json.dumps(
                {"error": "那個日期已被預訂，請換其他日期。"}, ensure_ascii=False
            )

        user = s.get(User, line_user_id)
        if user is None:
            user = User(line_user_id=line_user_id)
            s.add(user)
            s.flush()
        user_lang = user.preferred_language or "zh"

        booking = Booking(
            line_user_id=line_user_id,
            room_type_id=rt_uuid,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            extra_beds=extra_beds,
            total_price=quote["total"],
            customer_name=customer_name,
            notes=notes or "",
            status="confirmed",
        )
        s.add(booking)
        s.flush()

        booking_id_str = str(booking.id)
        room_name = room.name
        total_price = quote["total"]
        nights = quote["nights"]

    from app.config import get_settings
    from app.notifications import send_booking_stay_confirmation

    settings = get_settings()
    lc = LineClient(channel_access_token=settings.line_channel_access_token)
    with contextlib.suppress(Exception):
        send_booking_stay_confirmation(
            line_user_id=line_user_id,
            room_name=room_name,
            check_in=check_in,
            check_out=check_out,
            nights=nights,
            guests=guests,
            total_price=total_price,
            customer_name=customer_name,
            notes=notes or "",
            preferred_language=user_lang,
            line_client=lc,
            owner_line_user_id=settings.owner_line_user_id,
        )

    return json.dumps(
        {
            "success": True,
            "booking_id": booking_id_str,
            "room_type": room_name,
            "check_in": check_in_str,
            "check_out": check_out_str,
            "nights": nights,
            "guests": guests,
            "total": total_price,
            "customer_name": customer_name,
        },
        ensure_ascii=False,
    )


def _get_my_bookings(line_user_id: str) -> str:
    import zoneinfo
    from datetime import datetime

    today = datetime.now(tz=zoneinfo.ZoneInfo("Asia/Taipei")).date()
    with session_scope() as s:
        rows = s.execute(
            select(
                Booking.id,
                Booking.check_in,
                Booking.check_out,
                Booking.guests,
                Booking.total_price,
                RoomType.name.label("room_name"),
            )
            .join(RoomType, Booking.room_type_id == RoomType.id)
            .where(
                Booking.line_user_id == line_user_id,
                Booking.status == "confirmed",
                Booking.check_out >= today,
            )
            .order_by(Booking.check_in)
        ).all()
        result = [
            {
                "id": str(r.id),
                "room_type": r.room_name,
                "check_in": r.check_in.isoformat(),
                "check_out": r.check_out.isoformat(),
                "guests": r.guests,
                "total": r.total_price,
            }
            for r in rows
        ]
    if not result:
        return json.dumps({"bookings": [], "message": "No upcoming bookings found."})
    return json.dumps({"bookings": result}, ensure_ascii=False)


def _cancel_booking(booking_id: str, *, line_user_id: str) -> str:
    try:
        bk_uuid = uuid.UUID(booking_id)
    except (ValueError, TypeError):
        return json.dumps({"error": "Invalid booking ID format."})

    room_name = ""
    range_str = ""
    with session_scope() as s:
        booking = s.get(Booking, bk_uuid)
        if booking is None or booking.line_user_id != line_user_id:
            return json.dumps({"error": "Booking not found."})
        if booking.status != "confirmed":
            return json.dumps(
                {"error": f"Cannot cancel booking with status '{booking.status}'."}
            )
        room = s.get(RoomType, booking.room_type_id)
        room_name = room.name if room else ""
        range_str = f"{booking.check_in.isoformat()} → {booking.check_out.isoformat()}"
        booking.status = "cancelled"

    from app.config import get_settings

    lc = LineClient(channel_access_token=get_settings().line_channel_access_token)
    msg = f"❌ 已取消訂房\n房型：{room_name}\n日期：{range_str}"
    with contextlib.suppress(Exception):
        lc.push(line_user_id=line_user_id, messages=[ReplyMessage.text(msg)])

    return json.dumps(
        {"success": True, "room_type": room_name, "cancelled": range_str},
        ensure_ascii=False,
    )


def execute_tool(name: str, tool_input: dict, *, line_user_id: str) -> str:
    if name == "get_room_types":
        return _get_room_types()
    if name == "quote_stay":
        rt = tool_input.get("room_type_id")
        ci = tool_input.get("check_in")
        co = tool_input.get("check_out")
        guests = tool_input.get("guests")
        if not rt or not ci or not co or guests is None:
            return json.dumps(
                {"error": "missing required fields: room_type_id, check_in, check_out, guests"}
            )
        return _quote_stay(rt, ci, co, int(guests), int(tool_input.get("extra_beds") or 0))
    if name == "check_availability":
        ci = tool_input.get("check_in")
        co = tool_input.get("check_out")
        if not ci or not co:
            return json.dumps({"error": "missing required fields: check_in, check_out"})
        guests = tool_input.get("guests")
        return _check_availability(ci, co, int(guests) if guests is not None else None)
    if name == "book_stay":
        rt = tool_input.get("room_type_id")
        ci = tool_input.get("check_in")
        co = tool_input.get("check_out")
        guests = tool_input.get("guests")
        cname = tool_input.get("customer_name")
        if not rt or not ci or not co or guests is None or not cname:
            return json.dumps(
                {"error": "missing required fields: room_type_id, check_in, check_out, guests, customer_name"}
            )
        return _book_stay(
            rt,
            ci,
            co,
            int(guests),
            cname,
            int(tool_input.get("extra_beds") or 0),
            tool_input.get("notes"),
            line_user_id=line_user_id,
        )
    if name == "get_my_bookings":
        return _get_my_bookings(line_user_id)
    if name == "cancel_booking":
        bk_id = tool_input.get("booking_id")
        if not bk_id:
            return json.dumps({"error": "missing required field: booking_id"})
        return _cancel_booking(bk_id, line_user_id=line_user_id)
    return json.dumps({"error": f"Unknown tool: {name!r}"})
