from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import session_scope
from app.models import Booking, RoomType


def available_units(
    room_type_id: uuid.UUID,
    check_in: date,
    check_out: date,
    session: Session | None = None,
) -> int:
    """How many units of a room type are free across [check_in, check_out).

    Counts confirmed bookings whose date range overlaps (half-open, so
    back-to-back stays where check_out == next check_in do not collide) and
    subtracts them from the room type's inventory. Returns >= 0.
    """

    def _compute(s: Session) -> int:
        room = s.get(RoomType, room_type_id)
        if room is None:
            return 0
        overlapping = s.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.room_type_id == room_type_id,
                Booking.status == "confirmed",
                Booking.check_in < check_out,
                Booking.check_out > check_in,
            )
        ).scalar_one()
        return max(room.quantity - overlapping, 0)

    if session is not None:
        return _compute(session)
    with session_scope() as s:
        return _compute(s)


def is_available(
    room_type_id: uuid.UUID,
    check_in: date,
    check_out: date,
    session: Session | None = None,
) -> bool:
    return available_units(room_type_id, check_in, check_out, session) > 0
