from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Literal

from anthropic import Anthropic

from app.config import get_settings
from app.cost_tracker import UsageCounts


@dataclass(frozen=True)
class ChatTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class AnthropicCallResult:
    text: str
    usage: UsageCounts


@lru_cache
def _client() -> Anthropic:
    return Anthropic(api_key=get_settings().anthropic_api_key)


def call_claude(
    *,
    system_prompt: str,
    history: list[ChatTurn],
    user_message: str,
    model: str,
    max_tokens: int = 1024,
) -> AnthropicCallResult:
    messages = [{"role": t.role, "content": t.content} for t in history]
    messages.append({"role": "user", "content": user_message})

    response = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )

    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()

    u = response.usage
    usage = UsageCounts(
        input_tokens=getattr(u, "input_tokens", 0) or 0,
        output_tokens=getattr(u, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
    )
    return AnthropicCallResult(text=text, usage=usage)


def call_claude_with_tools(
    *,
    system_prompt: str,
    history: list[ChatTurn],
    user_message: str,
    model: str,
    tools: list[dict],
    tool_executor: Callable[[str, dict], str],
    max_tokens: int = 1024,
    max_tool_turns: int = 5,
) -> AnthropicCallResult:
    messages: list[dict] = [{"role": t.role, "content": t.content} for t in history]
    messages.append({"role": "user", "content": user_message})

    total_input = total_output = total_cache_read = total_cache_write = 0

    for _ in range(max_tool_turns):
        response = _client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            tools=tools,
        )
        u = response.usage
        total_input += getattr(u, "input_tokens", 0) or 0
        total_output += getattr(u, "output_tokens", 0) or 0
        total_cache_read += getattr(u, "cache_read_input_tokens", 0) or 0
        total_cache_write += getattr(u, "cache_creation_input_tokens", 0) or 0

        if response.stop_reason != "tool_use":
            parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            return AnthropicCallResult(
                text="".join(parts).strip(),
                usage=UsageCounts(total_input, total_output, total_cache_read, total_cache_write),
            )

        messages.append({"role": "assistant", "content": response.content})
        tool_results = [
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": tool_executor(block.name, block.input),
            }
            for block in response.content
            if getattr(block, "type", None) == "tool_use"
        ]
        messages.append({"role": "user", "content": tool_results})

    # max_tool_turns exhausted — one final call without tools to get a text response
    response = _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    u = response.usage
    total_input += getattr(u, "input_tokens", 0) or 0
    total_output += getattr(u, "output_tokens", 0) or 0
    total_cache_read += getattr(u, "cache_read_input_tokens", 0) or 0
    total_cache_write += getattr(u, "cache_creation_input_tokens", 0) or 0
    parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    return AnthropicCallResult(
        text="".join(parts).strip(),
        usage=UsageCounts(total_input, total_output, total_cache_read, total_cache_write),
    )
