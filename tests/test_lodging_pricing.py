import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import uuid
from datetime import date

import pytest

from app.db import session_scope
from app.lodging_pricing import QuoteError, classify_day, price_for_night, quote_stay
from app.models import HolidayDate, RoomType


def _seed_room(
    *,
    capacity: int = 8,
    max_capacity: int = 8,
    max_extra_beds: int = 0,
    price_weekday: int = 12000,
    price_peak: int = 18000,
    price_holiday: int = 21000,
    extra_bed_price: int = 800,
) -> RoomType:
    room = RoomType(
        id=uuid.uuid4(),
        name="包棟-8人",
        capacity=capacity,
        max_capacity=max_capacity,
        max_extra_beds=max_extra_beds,
        quantity=1,
        price_weekday=price_weekday,
        price_peak=price_peak,
        price_holiday=price_holiday,
        extra_bed_price=extra_bed_price,
    )
    with session_scope() as s:
        s.add(room)
    return room


# ---- classify_day -------------------------------------------------------------

def test_classify_weekday():
    with session_scope() as s:
        assert classify_day(date(2026, 7, 6), s) == "weekday"  # Monday


def test_classify_peak_friday_and_sunday():
    with session_scope() as s:
        assert classify_day(date(2026, 7, 10), s) == "peak"  # Friday
        assert classify_day(date(2026, 7, 12), s) == "peak"  # Sunday


def test_classify_holiday_saturday():
    with session_scope() as s:
        assert classify_day(date(2026, 7, 11), s) == "holiday"  # Saturday


def test_holiday_override_beats_weekday_rule():
    with session_scope() as s:
        s.add(HolidayDate(date=date(2026, 7, 6), day_type="holiday"))
    with session_scope() as s:
        # Monday would be weekday, but override forces holiday
        assert classify_day(date(2026, 7, 6), s) == "holiday"


# ---- price_for_night ----------------------------------------------------------

def test_price_for_night_by_day_type():
    room = _seed_room()
    assert price_for_night(room, "weekday") == 12000
    assert price_for_night(room, "peak") == 18000
    assert price_for_night(room, "holiday") == 21000


# ---- quote_stay ---------------------------------------------------------------

def test_quote_mixed_multi_night():
    room = _seed_room()
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        # 8/15 Sat (holiday) + 8/16 Sun (peak), checkout 8/17
        quote = quote_stay(room, date(2026, 8, 15), date(2026, 8, 17), guests=8, session=s)
    assert quote["nights"] == 2
    assert quote["room_total"] == 21000 + 18000
    assert quote["extra_bed_total"] == 0
    assert quote["total"] == 39000
    assert [n["day_type"] for n in quote["per_night"]] == ["holiday", "peak"]


def test_quote_extra_bed_math():
    room = _seed_room(capacity=16, max_capacity=21, max_extra_beds=5)
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        # 2 nights, 3 extra beds × 800 × 2 nights = 4800
        quote = quote_stay(
            room, date(2026, 8, 15), date(2026, 8, 17), guests=19, extra_beds=3, session=s
        )
    assert quote["nights"] == 2
    assert quote["extra_bed_total"] == 3 * 800 * 2
    assert quote["total"] == quote["room_total"] + 4800


def test_quote_rejects_check_out_not_after_check_in():
    room = _seed_room()
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        with pytest.raises(QuoteError):
            quote_stay(room, date(2026, 8, 15), date(2026, 8, 15), guests=8, session=s)


def test_quote_rejects_over_max_capacity():
    room = _seed_room(capacity=8, max_capacity=8)
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        with pytest.raises(QuoteError):
            quote_stay(room, date(2026, 8, 15), date(2026, 8, 17), guests=9, session=s)


def test_quote_rejects_guests_over_capacity_without_extra_beds():
    room = _seed_room(capacity=16, max_capacity=21, max_extra_beds=5)
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        # 18 guests needs 2 extra beds but 0 requested
        with pytest.raises(QuoteError):
            quote_stay(room, date(2026, 8, 15), date(2026, 8, 17), guests=18, session=s)


def test_quote_rejects_too_many_extra_beds():
    room = _seed_room(capacity=16, max_capacity=21, max_extra_beds=5)
    with session_scope() as s:
        room = s.get(RoomType, room.id)
        with pytest.raises(QuoteError):
            quote_stay(
                room, date(2026, 8, 15), date(2026, 8, 17), guests=16, extra_beds=6, session=s
            )
