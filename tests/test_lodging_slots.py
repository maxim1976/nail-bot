import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import uuid
from datetime import date

from app.db import session_scope
from app.lodging_slots import available_units, is_available
from app.models import Booking, RoomType, User


def _seed_room(quantity: int = 1) -> uuid.UUID:
    rid = uuid.uuid4()
    with session_scope() as s:
        s.add(RoomType(
            id=rid, name="包棟", capacity=8, max_capacity=8, quantity=quantity,
            price_weekday=12000, price_peak=18000, price_holiday=21000,
        ))
    return rid


def _seed_booking(
    room_id: uuid.UUID,
    check_in: date,
    check_out: date,
    *,
    status: str = "confirmed",
    user: str = "U_lodge",
) -> None:
    with session_scope() as s:
        s.merge(User(line_user_id=user))
    with session_scope() as s:
        s.add(Booking(
            id=uuid.uuid4(),
            line_user_id=user,
            room_type_id=room_id,
            check_in=check_in,
            check_out=check_out,
            guests=8,
            total_price=24000,
            status=status,
        ))


def test_no_bookings_all_units_available():
    rid = _seed_room(quantity=1)
    assert available_units(rid, date(2026, 8, 15), date(2026, 8, 17)) == 1
    assert is_available(rid, date(2026, 8, 15), date(2026, 8, 17)) is True


def test_overlapping_booking_blocks_quantity_one():
    rid = _seed_room(quantity=1)
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17))
    # Requested 8/16–8/18 overlaps the 8/15–8/17 stay
    assert available_units(rid, date(2026, 8, 16), date(2026, 8, 18)) == 0
    assert is_available(rid, date(2026, 8, 16), date(2026, 8, 18)) is False


def test_back_to_back_does_not_collide():
    rid = _seed_room(quantity=1)
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17))
    # New stay starts exactly when the old one checks out — half-open, no overlap
    assert available_units(rid, date(2026, 8, 17), date(2026, 8, 19)) == 1
    assert is_available(rid, date(2026, 8, 17), date(2026, 8, 19)) is True


def test_non_overlapping_range_available():
    rid = _seed_room(quantity=1)
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17))
    assert is_available(rid, date(2026, 9, 1), date(2026, 9, 3)) is True


def test_cancelled_booking_does_not_block():
    rid = _seed_room(quantity=1)
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17), status="cancelled")
    assert available_units(rid, date(2026, 8, 15), date(2026, 8, 17)) == 1


def test_quantity_two_allows_one_overlap():
    rid = _seed_room(quantity=2)
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17), user="U_a")
    assert available_units(rid, date(2026, 8, 15), date(2026, 8, 17)) == 1
    _seed_booking(rid, date(2026, 8, 15), date(2026, 8, 17), user="U_b")
    assert available_units(rid, date(2026, 8, 15), date(2026, 8, 17)) == 0


def test_unknown_room_returns_zero():
    assert available_units(uuid.uuid4(), date(2026, 8, 15), date(2026, 8, 17)) == 0
