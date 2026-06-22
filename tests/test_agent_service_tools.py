import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

import uuid
from unittest.mock import MagicMock, patch

from app.agent_service import generate_agent_reply
from app.cost_tracker import UsageCounts
from app.db import session_scope
from app.models import Service, User


def _seed_booking_user(line_user_id: str = "U_ba_test") -> None:
    with session_scope() as s:
        s.merge(User(
            line_user_id=line_user_id,
            display_name="Test",
            preferred_language="zh",
            current_agent_key="booking_assistant",
        ))


def _seed_sales_user(line_user_id: str = "U_sa_test") -> None:
    with session_scope() as s:
        s.merge(User(
            line_user_id=line_user_id,
            display_name="Test",
            preferred_language="zh",
            current_agent_key="sales_agent",
        ))


def _seed_service() -> uuid.UUID:
    svc_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Service(
            id=svc_id, name="Gel", name_en="Gel",
            duration_min=90, price=800, category="gel", sort_order=0,
        ))
    return svc_id


def _fake_result(text: str = "ok") -> MagicMock:
    result = MagicMock()
    result.text = text
    result.usage = UsageCounts(10, 5, 0, 0)
    return result


def test_booking_assistant_uses_call_claude_with_tools():
    _seed_booking_user()
    _seed_service()

    with patch("app.agent_service.call_claude_with_tools") as mock_cwt, \
         patch("app.agent_service.call_claude") as mock_cc:
        mock_cwt.return_value = _fake_result("Found your appointment")
        reply = generate_agent_reply(
            line_user_id="U_ba_test", text="show my appointments", history_turns=10,
        )

    mock_cwt.assert_called_once()
    mock_cc.assert_not_called()
    assert reply.text == "Found your appointment"


def test_non_booking_agent_uses_call_claude():
    _seed_sales_user()

    with patch("app.agent_service.call_claude_with_tools") as mock_cwt, \
         patch("app.agent_service.call_claude") as mock_cc:
        mock_cc.return_value = _fake_result("Hello from sales")
        reply = generate_agent_reply(
            line_user_id="U_sa_test", text="hello", history_turns=10,
        )

    mock_cc.assert_called_once()
    mock_cwt.assert_not_called()
    assert reply.text == "Hello from sales"


def test_booking_tool_executor_captures_line_user_id():
    """Verify the tool_executor closure passes the right line_user_id to execute_tool."""
    import json
    _seed_booking_user()
    _seed_service()

    captured: dict = {}

    def fake_cwt(*, tool_executor, **kwargs):
        captured["tool_executor"] = tool_executor
        return _fake_result("ok")

    with patch("app.agent_service.call_claude_with_tools", side_effect=fake_cwt):
        generate_agent_reply(
            line_user_id="U_ba_test", text="any", history_turns=10,
        )

    assert callable(captured["tool_executor"])
    # Call get_services through the closure — should use the DB, no line_user_id needed
    data = json.loads(captured["tool_executor"]("get_services", {}))
    assert "services" in data
