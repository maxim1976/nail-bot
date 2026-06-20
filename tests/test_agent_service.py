from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agent_service import AgentReply, generate_agent_reply
from app.cost_tracker import UsageCounts
from app.db import session_scope
from app.models import User


def _make_user(agent_key: str = "booking_assistant", lang: str = "zh") -> None:
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key=agent_key, preferred_language=lang))


def _mock_result(text: str) -> MagicMock:
    from app.anthropic_client import AnthropicCallResult
    return AnthropicCallResult(
        text=text,
        usage=UsageCounts(input_tokens=10, output_tokens=5, cache_read_tokens=0, cache_write_tokens=0),
    )


@patch("app.agent_service.call_claude")
def test_generate_agent_reply_returns_text(mock_call):
    _make_user()
    mock_call.return_value = _mock_result("Hello there!")
    result = generate_agent_reply(line_user_id="U001", text="Hi", history_turns=5)
    assert isinstance(result, AgentReply)
    assert result.text == "Hello there!"
    assert result.cost_usd >= 0.0


@patch("app.agent_service.call_claude")
def test_generate_agent_reply_strips_lang_sentinel(mock_call):
    _make_user(lang="zh")
    mock_call.return_value = _mock_result("[LANG:en] Hello! How can I help?")
    result = generate_agent_reply(line_user_id="U001", text="Hello", history_turns=5)
    assert result.text == "Hello! How can I help?"


@patch("app.agent_service.call_claude")
def test_generate_agent_reply_saves_detected_language(mock_call):
    _make_user(lang="zh")
    mock_call.return_value = _mock_result("[LANG:en] Hello! How can I help?")
    generate_agent_reply(line_user_id="U001", text="Hello", history_turns=5)
    with session_scope() as s:
        user = s.get(User, "U001")
        assert user.preferred_language == "en"


@patch("app.agent_service.call_claude")
def test_generate_agent_reply_no_sentinel_keeps_language(mock_call):
    _make_user(lang="zh")
    mock_call.return_value = _mock_result("您好！")
    generate_agent_reply(line_user_id="U001", text="你好", history_turns=5)
    with session_scope() as s:
        user = s.get(User, "U001")
        assert user.preferred_language == "zh"


@patch("app.agent_service.call_claude")
def test_generate_agent_reply_saves_conversation_history(mock_call):
    _make_user()
    mock_call.return_value = _mock_result("reply text")
    generate_agent_reply(line_user_id="U001", text="question", history_turns=5)
    from sqlalchemy import select
    from app.models import Message
    with session_scope() as s:
        msgs = s.execute(select(Message).order_by(Message.created_at)).scalars().all()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "question"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "reply text"


def test_generate_agent_reply_raises_if_no_agent_key():
    with session_scope() as s:
        s.add(User(line_user_id="U002", current_agent_key=None))
    with pytest.raises(ValueError, match="no current_agent_key"):
        generate_agent_reply(line_user_id="U002", text="hi", history_turns=5)
