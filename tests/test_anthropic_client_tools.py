import os

os.environ.setdefault("ADMIN_JWT_SECRET", "test-secret-key-for-testing-only-32ch")

from unittest.mock import MagicMock, patch

from app.anthropic_client import ChatTurn, call_claude_with_tools

_TOOLS = [
    {
        "name": "echo",
        "description": "Echoes input back",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }
]


def _mock_response(stop_reason: str, content: list) -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content
    resp.usage = MagicMock(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return resp


def _text_block(text: str) -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _tool_use_block(name: str, tool_input: dict, tool_id: str = "t1") -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.id = tool_id
    b.name = name
    b.input = tool_input
    return b


def test_no_tool_call_returns_text_in_one_turn():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_response("end_turn", [_text_block("Hello")])

    with patch("app.anthropic_client._client", return_value=mock_client):
        result = call_claude_with_tools(
            system_prompt="sys",
            history=[],
            user_message="hi",
            model="claude-test",
            tools=_TOOLS,
            tool_executor=lambda n, i: "unused",
        )

    assert result.text == "Hello"
    assert mock_client.messages.create.call_count == 1


def test_one_tool_call_then_end_turn():
    mock_client = MagicMock()
    tool_block = _tool_use_block("echo", {"text": "hi"})
    mock_client.messages.create.side_effect = [
        _mock_response("tool_use", [tool_block]),
        _mock_response("end_turn", [_text_block("Done")]),
    ]

    with patch("app.anthropic_client._client", return_value=mock_client):
        result = call_claude_with_tools(
            system_prompt="sys",
            history=[],
            user_message="echo this",
            model="claude-test",
            tools=_TOOLS,
            tool_executor=lambda n, i: f"echoed: {i['text']}",
        )

    assert result.text == "Done"
    assert mock_client.messages.create.call_count == 2


def test_usage_accumulates_across_turns():
    mock_client = MagicMock()
    tool_block = _tool_use_block("echo", {"text": "x"})
    mock_client.messages.create.side_effect = [
        _mock_response("tool_use", [tool_block]),
        _mock_response("end_turn", [_text_block("ok")]),
    ]

    with patch("app.anthropic_client._client", return_value=mock_client):
        result = call_claude_with_tools(
            system_prompt="sys",
            history=[],
            user_message="hi",
            model="m",
            tools=_TOOLS,
            tool_executor=lambda n, i: "res",
        )

    # 2 turns × (10 input + 5 output) each
    assert result.usage.input_tokens == 20
    assert result.usage.output_tokens == 10


def test_max_tool_turns_exhausted_makes_final_text_call():
    mock_client = MagicMock()
    tool_block = _tool_use_block("echo", {"text": "x"})
    # 5 tool_use responses hit max_tool_turns; final call returns text
    mock_client.messages.create.side_effect = (
        [_mock_response("tool_use", [tool_block])] * 5
        + [_mock_response("end_turn", [_text_block("fallback")])]
    )

    with patch("app.anthropic_client._client", return_value=mock_client):
        result = call_claude_with_tools(
            system_prompt="sys",
            history=[],
            user_message="hi",
            model="m",
            tools=_TOOLS,
            tool_executor=lambda n, i: "res",
            max_tool_turns=5,
        )

    assert result.text == "fallback"
    assert mock_client.messages.create.call_count == 6  # 5 loop + 1 final
