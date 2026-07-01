from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.db import session_scope
from app.event_router import handle_event
from app.models import Service


def _make_event(text: str, user_id: str = "U123") -> dict:
    return {
        "type": "message",
        "replyToken": "tok",
        "source": {"userId": user_id},
        "message": {"type": "text", "text": text},
    }


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.get_display_name.return_value = "Test User"
    return client


def test_services_trigger_returns_carousel():
    """本月優惠 message returns a flex carousel regardless of persona."""
    with session_scope() as s:
        s.add(Service(
            id=uuid.uuid4(),
            name="日式光療凝膠",
            name_en="", name_tl="", name_id="", name_vi="",
            duration_min=90, price=1200,
            in_carousel=True, is_available=True,
        ))

    client = _mock_client()
    handle_event(_make_event("本月優惠"), line_client=client, rich_menu_id=None)

    client.reply.assert_called_once()
    messages = client.reply.call_args.kwargs["messages"]
    assert messages[0].payload["type"] == "flex"
    assert messages[0].payload["altText"] == "本月優惠"


def test_services_trigger_no_services_returns_fallback_text():
    """本月優惠 with no qualifying services replies with fallback text."""
    client = _mock_client()
    handle_event(_make_event("本月優惠", user_id="U999"), line_client=client, rich_menu_id=None)

    client.reply.assert_called_once()
    messages = client.reply.call_args.kwargs["messages"]
    assert messages[0].payload["type"] == "text"
    assert "敬請期待" in messages[0].payload["text"]


def test_services_trigger_fires_without_persona_selected():
    """Handler must not require a persona — fires even for new users."""
    with session_scope() as s:
        s.add(Service(
            id=uuid.uuid4(),
            name="手繪彩繪設計",
            name_en="", name_tl="", name_id="", name_vi="",
            duration_min=120, price=1800,
            in_carousel=True, is_available=True,
        ))

    client = _mock_client()
    # Fresh user — no persona set, never sent a message before
    handle_event(_make_event("本月優惠", user_id="U_FRESH"), line_client=client, rich_menu_id=None)

    client.reply.assert_called_once()
    assert client.reply.call_args.kwargs["messages"][0].payload["type"] == "flex"
