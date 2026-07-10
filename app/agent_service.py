from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.anthropic_client import AnthropicCallResult, ChatTurn, call_claude, call_claude_with_tools
from app.config import get_settings
from app.cost_tracker import record_call
from app.db import session_scope
from app.models import Conversation, Message, RoomType, Service, StudioProfile, User
from app.personas import system_prompt_for

_LANG_SENTINEL = re.compile(r"^\[LANG:([a-z]{2})\]\s*")
_VALID_LANGS = {"zh", "en", "tl", "id", "vi"}

_MD_BOLD_ITALIC = re.compile(r'\*{1,3}([^*\n]+?)\*{1,3}')
_MD_UNDERLINE = re.compile(r'_{1,2}([^_\n]+?)_{1,2}')
_MD_STRIKE = re.compile(r'~~([^~\n]+?)~~')
_MD_HEADING = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_MD_CODE = re.compile(r'`([^`\n]+?)`')


def _strip_markdown(text: str) -> str:
    text = _MD_BOLD_ITALIC.sub(r'\1', text)
    text = _MD_UNDERLINE.sub(r'\1', text)
    text = _MD_STRIKE.sub(r'\1', text)
    text = _MD_HEADING.sub('', text)
    text = _MD_CODE.sub(r'\1', text)
    return text


@dataclass(frozen=True)
class AgentReply:
    text: str
    cost_usd: float


def _parse_lang_sentinel(text: str) -> tuple[str | None, str]:
    m = _LANG_SENTINEL.match(text)
    if m and m.group(1) in _VALID_LANGS:
        return m.group(1), text[m.end():]
    return None, text


def _load_history(conv_id: object, limit: int) -> list[ChatTurn]:
    with session_scope() as s:
        rows = s.execute(
            select(Message.role, Message.content)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
        ).all()
    return [ChatTurn(role=r.role, content=r.content) for r in rows[-limit:]]


def _get_or_create_conversation(line_user_id: str, agent_key: str) -> object:
    with session_scope() as s:
        conv = s.execute(
            select(Conversation).where(
                Conversation.line_user_id == line_user_id,
                Conversation.agent_key == agent_key,
            )
        ).scalar_one_or_none()
        if conv is None:
            conv = Conversation(line_user_id=line_user_id, agent_key=agent_key)
            s.add(conv)
            s.flush()
        return conv.id


def _build_studio_section() -> tuple[str, str, str]:
    with session_scope() as s:
        profile = s.get(StudioProfile, 1)
        services = (
            s.execute(
                select(Service)
                .where(Service.is_available == True)  # noqa: E712
                .order_by(Service.sort_order)
            )
            .scalars()
            .all()
        )

    if profile:
        studio_name = profile.studio_name
        parts = []
        if profile.address:
            parts.append(f"Address: {profile.address}")
        if profile.phone:
            parts.append(f"Phone: {profile.phone}")
        if profile.instagram:
            parts.append(f"Instagram: {profile.instagram}")
        if profile.website:
            parts.append(f"Website: {profile.website}")
        if profile.cancellation_policy:
            parts.append(f"Cancellation policy: {profile.cancellation_policy}")
        if profile.aftercare_notes:
            parts.append(f"Aftercare: {profile.aftercare_notes}")
        if profile.ai_persona_notes:
            parts.append(f"\nAdditional instructions: {profile.ai_persona_notes}")
        studio_section = "\n".join(parts) if parts else "(Studio info not configured yet)"
    else:
        studio_name = "Hualienvibe"
        studio_section = "(Studio info not configured yet)"

    if services:
        rows = []
        for svc in services:
            notes = f" [{svc.agent_notes}]" if svc.agent_notes else ""
            rows.append(
                f"- {svc.name} ({svc.name_en}) — {svc.duration_min}min — NT${svc.price}{notes}"
            )
        services_section = "\n".join(rows)
    else:
        services_section = "(No services configured yet)"

    return studio_name, studio_section, services_section


def _build_rooms_section() -> str:
    with session_scope() as s:
        rooms = (
            s.execute(
                select(RoomType)
                .where(RoomType.is_available == True)  # noqa: E712
                .order_by(RoomType.sort_order)
            )
            .scalars()
            .all()
        )
    if not rooms:
        return "(No room types configured yet)"
    rows = []
    for r in rooms:
        rows.append(
            f"- {r.name} (id={r.id}) — 適合 {r.capacity} 人（最多 {r.max_capacity}）"
            f" — 平日 NT${r.price_weekday} / 旺日 NT${r.price_peak} / 連續假日 NT${r.price_holiday}"
        )
    return "\n".join(rows)


def _build_system_prompt(agent_key: str, preferred_language: str) -> str:
    import zoneinfo
    from datetime import datetime

    settings = get_settings()
    if agent_key == "booking_assistant":
        studio_name, studio_section, services_section = _build_studio_section()
        today = datetime.now(zoneinfo.ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d (%A)")
        return system_prompt_for(
            agent_key,
            studio_name=studio_name,
            studio_section=studio_section,
            services_section=services_section,
            preferred_language=preferred_language,
            today=today,
        )
    if agent_key == "lodging_assistant":
        studio_name, studio_section, _ = _build_studio_section()
        rooms_section = _build_rooms_section()
        today = datetime.now(zoneinfo.ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d (%A)")
        return system_prompt_for(
            agent_key,
            studio_name=studio_name,
            studio_section=studio_section,
            rooms_section=rooms_section,
            preferred_language=preferred_language,
            today=today,
        )
    if agent_key == "sales_agent":
        seller_line_id = settings.seller_line_id or "（請洽開發者）"
        return system_prompt_for(
            agent_key,
            seller_line_id=seller_line_id,
            preferred_language=preferred_language,
        )
    raise ValueError(f"unknown agent_key: {agent_key!r}")


def generate_agent_reply(*, line_user_id: str, text: str, history_turns: int) -> AgentReply:
    settings = get_settings()

    with session_scope() as s:
        user = s.get(User, line_user_id)
        if user is None or user.current_agent_key is None:
            raise ValueError(f"user {line_user_id!r} has no current_agent_key set")
        agent_key = user.current_agent_key
        preferred_language = user.preferred_language or "zh"

    conv_id = _get_or_create_conversation(line_user_id, agent_key)
    history = _load_history(conv_id, limit=history_turns)
    system_prompt = _build_system_prompt(agent_key, preferred_language)

    result: AnthropicCallResult
    if agent_key in ("booking_assistant", "lodging_assistant"):
        if agent_key == "lodging_assistant":
            from app.lodging_tools import LODGING_TOOLS as _TOOLS
            from app.lodging_tools import execute_tool as _execute_tool
        else:
            from app.agent_tools import BOOKING_TOOLS as _TOOLS
            from app.agent_tools import execute_tool as _execute_tool
        tool_executor = lambda name, inp: _execute_tool(name, inp, line_user_id=line_user_id)
        result = call_claude_with_tools(
            system_prompt=system_prompt,
            history=history,
            user_message=text,
            model=settings.anthropic_model,
            tools=_TOOLS,
            tool_executor=tool_executor,
        )
    else:
        result = call_claude(
            system_prompt=system_prompt,
            history=history,
            user_message=text,
            model=settings.anthropic_model,
        )

    detected_lang, clean_text = _parse_lang_sentinel(_strip_markdown(result.text))
    cost = record_call(result.usage, ceiling_usd=settings.daily_cost_ceiling_usd)

    if detected_lang:
        with session_scope() as s:
            user = s.get(User, line_user_id)
            if user:
                user.preferred_language = detected_lang

    with session_scope() as s:
        s.add(Message(conversation_id=conv_id, role="user", content=text))
        s.add(
            Message(
                conversation_id=conv_id,
                role="assistant",
                content=clean_text,
                token_input=result.usage.input_tokens,
                token_output=result.usage.output_tokens,
                cost_usd=Decimal(str(cost)),
            )
        )
        conv = s.get(Conversation, conv_id)
        if conv:
            conv.message_count += 2

    return AgentReply(text=clean_text, cost_usd=cost)
