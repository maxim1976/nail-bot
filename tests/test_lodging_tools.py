import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import json
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.db import session_scope
from app.lodging_tools import LODGING_TOOLS, execute_tool
from app.models import Booking, RoomType, User

CI = "2026-08-15"  # Sat (holiday)
CO = "2026-08-17"  # checkout Mon; nights = 8/15 holiday + 8/16 peak


def _seed_user(line_user_id: str = "U_lodge") -> None:
    with session_scope() as s:
        s.merge(User(line_user_id=line_user_id, display_name="Test", preferred_language="zh"))


def _seed_room(
    *,
    capacity: int = 8,
    max_capacity: int = 8,
    max_extra_beds: int = 0,
    quantity: int = 1,
) -> uuid.UUID:
    rid = uuid.uuid4()
    with session_scope() as s:
        s.add(RoomType(
            id=rid, name="包棟-8人", capacity=capacity, max_capacity=max_capacity,
            max_extra_beds=max_extra_beds, quantity=quantity,
            price_weekday=12000, price_peak=18000, price_holiday=21000,
        ))
    return rid


def test_lodging_tools_has_six_entries():
    names = [t["name"] for t in LODGING_TOOLS]
    assert names == [
        "get_room_types",
        "quote_stay",
        "check_availability",
        "book_stay",
        "get_my_bookings",
        "cancel_booking",
    ]


def test_get_room_types_returns_available():
    rid = _seed_room()
    result = json.loads(execute_tool("get_room_types", {}, line_user_id="U_lodge"))
    ids = [r["id"] for r in result["room_types"]]
    assert str(rid) in ids
    room = next(r for r in result["room_types"] if r["id"] == str(rid))
    assert room["price_holiday"] == 21000


def test_quote_stay_happy_path():
    rid = _seed_room()
    result = json.loads(execute_tool(
        "quote_stay",
        {"room_type_id": str(rid), "check_in": CI, "check_out": CO, "guests": 8},
        line_user_id="U_lodge",
    ))
    assert result["nights"] == 2
    assert result["total"] == 21000 + 18000  # holiday + peak


def test_quote_stay_over_capacity_returns_error():
    rid = _seed_room(capacity=8, max_capacity=8)
    result = json.loads(execute_tool(
        "quote_stay",
        {"room_type_id": str(rid), "check_in": CI, "check_out": CO, "guests": 9},
        line_user_id="U_lodge",
    ))
    assert "error" in result


def test_check_availability_lists_free_rooms():
    rid = _seed_room()
    result = json.loads(execute_tool(
        "check_availability",
        {"check_in": CI, "check_out": CO, "guests": 8},
        line_user_id="U_lodge",
    ))
    ids = [r["id"] for r in result["available"]]
    assert str(rid) in ids


def test_check_availability_filters_by_guests():
    rid = _seed_room(capacity=8, max_capacity=8)
    result = json.loads(execute_tool(
        "check_availability",
        {"check_in": CI, "check_out": CO, "guests": 20},
        line_user_id="U_lodge",
    ))
    ids = [r["id"] for r in result["available"]]
    assert str(rid) not in ids


def test_book_stay_happy_path():
    _seed_user()
    rid = _seed_room()
    with patch("app.lodging_tools.LineClient") as MockLC:
        MockLC.return_value = MagicMock()
        result = json.loads(execute_tool(
            "book_stay",
            {
                "room_type_id": str(rid),
                "check_in": CI,
                "check_out": CO,
                "guests": 8,
                "customer_name": "小明",
            },
            line_user_id="U_lodge",
        ))
    assert result["success"] is True
    assert result["total"] == 39000
    with session_scope() as s:
        bk = s.get(Booking, uuid.UUID(result["booking_id"]))
        assert bk is not None
        assert bk.status == "confirmed"
        assert bk.total_price == 39000


def test_book_stay_double_book_rejected():
    _seed_user("U_a")
    _seed_user("U_b")
    rid = _seed_room(quantity=1)
    with patch("app.lodging_tools.LineClient") as MockLC:
        MockLC.return_value = MagicMock()
        first = json.loads(execute_tool(
            "book_stay",
            {"room_type_id": str(rid), "check_in": CI, "check_out": CO,
             "guests": 8, "customer_name": "A"},
            line_user_id="U_a",
        ))
        assert first["success"] is True
        # Overlapping second booking on the single unit should fail
        second = json.loads(execute_tool(
            "book_stay",
            {"room_type_id": str(rid), "check_in": "2026-08-16", "check_out": "2026-08-18",
             "guests": 8, "customer_name": "B"},
            line_user_id="U_b",
        ))
    assert "error" in second


def test_get_my_bookings_returns_upcoming():
    _seed_user()
    rid = _seed_room()
    with patch("app.lodging_tools.LineClient") as MockLC:
        MockLC.return_value = MagicMock()
        execute_tool(
            "book_stay",
            {"room_type_id": str(rid), "check_in": CI, "check_out": CO,
             "guests": 8, "customer_name": "小明"},
            line_user_id="U_lodge",
        )
    result = json.loads(execute_tool("get_my_bookings", {}, line_user_id="U_lodge"))
    assert len(result["bookings"]) == 1
    assert result["bookings"][0]["room_type"] == "包棟-8人"


def test_cancel_booking_frees_the_dates():
    _seed_user()
    rid = _seed_room(quantity=1)
    with patch("app.lodging_tools.LineClient") as MockLC:
        MockLC.return_value = MagicMock()
        booked = json.loads(execute_tool(
            "book_stay",
            {"room_type_id": str(rid), "check_in": CI, "check_out": CO,
             "guests": 8, "customer_name": "小明"},
            line_user_id="U_lodge",
        ))
        cancelled = json.loads(execute_tool(
            "cancel_booking", {"booking_id": booked["booking_id"]}, line_user_id="U_lodge"
        ))
    assert cancelled["success"] is True
    from app.lodging_slots import is_available
    assert is_available(rid, date(2026, 8, 15), date(2026, 8, 17)) is True


def test_execute_tool_unknown_returns_error():
    result = json.loads(execute_tool("nope", {}, line_user_id="U_lodge"))
    assert "error" in result
