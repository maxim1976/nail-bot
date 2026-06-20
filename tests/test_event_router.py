from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.db import session_scope
from app.event_router import handle_event
from app.models import User


def _line_client() -> MagicMock:
    return MagicMock()


def _follow_event(user_id: str = "U001") -> dict:
    return {
        "type": "follow",
        "replyToken": "rt001",
        "source": {"userId": user_id},
    }


def _message_event(text: str, user_id: str = "U001") -> dict:
    return {
        "type": "message",
        "replyToken": "rt001",
        "source": {"userId": user_id},
        "message": {"type": "text", "text": text},
    }


def test_follow_creates_user_and_replies():
    lc = _line_client()
    lc.get_display_name.return_value = "Alice"
    handle_event(_follow_event(), line_client=lc, rich_menu_id=None)

    with session_scope() as s:
        user = s.get(User, "U001")
    assert user is not None
    assert user.current_agent_key is None
    lc.reply.assert_called_once()
    call_kwargs = lc.reply.call_args.kwargs
    msg = call_kwargs["messages"][0]
    labels = [i["action"]["label"] for i in msg.payload["quickReply"]["items"]]
    assert "💅 我要預約" in labels
    assert "🏪 了解此服務" in labels


def test_follow_sets_rich_menu():
    lc = _line_client()
    lc.get_display_name.return_value = None
    handle_event(_follow_event(), line_client=lc, rich_menu_id="RM001")
    lc.link_rich_menu_to_user.assert_called_once_with(line_user_id="U001", rich_menu_id="RM001")


def test_persona_selection_booking_assistant():
    with session_scope() as s:
        s.add(User(line_user_id="U001"))
    lc = _line_client()
    handle_event(_message_event("💅 我要預約"), line_client=lc, rich_menu_id=None)
    with session_scope() as s:
        user = s.get(User, "U001")
    assert user.current_agent_key == "booking_assistant"
    lc.reply.assert_called_once()


def test_persona_selection_sales_agent():
    with session_scope() as s:
        s.add(User(line_user_id="U001"))
    lc = _line_client()
    handle_event(_message_event("🏪 了解此服務"), line_client=lc, rich_menu_id=None)
    with session_scope() as s:
        user = s.get(User, "U001")
    assert user.current_agent_key == "sales_agent"


def test_message_without_persona_prompts_selection():
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key=None))
    lc = _line_client()
    handle_event(_message_event("hello"), line_client=lc, rich_menu_id=None)
    lc.reply.assert_called_once()
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "選擇" in msg_text or "身份" in msg_text


@patch("app.event_router.is_killed_today", return_value=True)
def test_killed_system_returns_offline(_):
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "休息" in msg_text


@patch("app.event_router.check_and_increment")
@patch("app.event_router.generate_agent_reply")
def test_rate_limited_hour_returns_cooldown(mock_reply, mock_rate):
    from app.rate_limiter import RateLimitDecision
    mock_rate.return_value = RateLimitDecision.BLOCKED_HOUR
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    mock_reply.assert_not_called()
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "頻繁" in msg_text


@patch("app.event_router.check_and_increment")
@patch("app.event_router.generate_agent_reply")
def test_normal_message_calls_agent(mock_reply, mock_rate):
    from app.agent_service import AgentReply
    from app.rate_limiter import RateLimitDecision
    mock_rate.return_value = RateLimitDecision.OK
    mock_reply.return_value = AgentReply(text="response", cost_usd=0.001)
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    mock_reply.assert_called_once()
    lc.reply.assert_called_once()


@patch("app.event_router.build_portfolio_carousel")
def test_portfolio_trigger_sends_carousel(mock_carousel):
    from app.line_client import ReplyMessage
    mock_carousel.return_value = ReplyMessage.flex("作品集", {"type": "carousel", "contents": []})
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("🖼 作品集"), line_client=lc, rich_menu_id=None)
    mock_carousel.assert_called_once()
    lc.reply.assert_called_once()
    msg = lc.reply.call_args.kwargs["messages"][0]
    assert msg.payload["type"] == "flex"


@patch("app.event_router.build_portfolio_carousel")
def test_portfolio_trigger_no_items_sends_text(mock_carousel):
    mock_carousel.return_value = None
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("🖼 作品集"), line_client=lc, rich_menu_id=None)
    msg = lc.reply.call_args.kwargs["messages"][0]
    assert msg.payload["type"] == "text"
    assert "敬請期待" in msg.payload["text"]
