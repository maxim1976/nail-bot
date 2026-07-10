from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import HolidayDate, RoomType


class QuoteError(ValueError):
    """Raised when a requested stay is invalid (bad dates, over capacity, etc.)."""


def classify_day(d: date, session: Session) -> str:
    """Classify a night's day-type: "weekday" | "peak" | "holiday".

    HolidayDate overrides take precedence; otherwise the weekday rule applies:
    Sat = holiday, Fri/Sun = peak, everything else = weekday.
    """
    override = session.get(HolidayDate, d)
    if override:
        return override.day_type
    dow = d.weekday()  # 0=Mon … 6=Sun
    if dow == 5:  # Sat
        return "holiday"
    if dow in (4, 6):  # Fri, Sun
        return "peak"
    return "weekday"


def price_for_night(room_type: RoomType, day_type: str) -> int:
    if day_type == "holiday":
        return room_type.price_holiday
    if day_type == "peak":
        return room_type.price_peak
    return room_type.price_weekday


def quote_stay(
    room_type: RoomType,
    check_in: date,
    check_out: date,
    guests: int,
    extra_beds: int = 0,
    session: Session | None = None,
) -> dict:
    """Price a stay across [check_in, check_out) night by night.

    Returns a dict with per-night breakdown and totals. Raises QuoteError on
    invalid input (bad date range, over capacity, too many extra beds, or not
    enough beds for the guest count).
    """
    if check_out <= check_in:
        raise QuoteError("check_out must be after check_in")
    if extra_beds < 0:
        raise QuoteError("extra_beds cannot be negative")
    if extra_beds > room_type.max_extra_beds:
        raise QuoteError(
            f"至多可加 {room_type.max_extra_beds} 床（要求 {extra_beds} 床）"
        )
    if guests > room_type.max_capacity:
        raise QuoteError(
            f"此房型最多容納 {room_type.max_capacity} 人（要求 {guests} 人）"
        )
    if guests > room_type.capacity + extra_beds:
        needed = guests - room_type.capacity
        raise QuoteError(
            f"{guests} 人需加 {needed} 床（本房型含 {room_type.capacity} 人）"
        )

    def _compute(s: Session) -> dict:
        per_night: list[dict] = []
        night = check_in
        while night < check_out:
            day_type = classify_day(night, s)
            price = price_for_night(room_type, day_type)
            per_night.append(
                {
                    "date": night.isoformat(),
                    "day_type": day_type,
                    "price": price,
                }
            )
            night += timedelta(days=1)

        nights = len(per_night)
        room_total = sum(n["price"] for n in per_night)
        extra_bed_total = extra_beds * room_type.extra_bed_price * nights
        total = room_total + extra_bed_total
        return {
            "room_type": room_type.name,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "nights": nights,
            "guests": guests,
            "extra_beds": extra_beds,
            "per_night": per_night,
            "room_total": room_total,
            "extra_bed_total": extra_bed_total,
            "total": total,
        }

    if session is not None:
        return _compute(session)
    with session_scope() as s:
        return _compute(s)
