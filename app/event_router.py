from __future__ import annotations

import contextlib
import logging
from typing import Any

from anthropic import RateLimitError

from app.agent_service import generate_agent_reply
from app.config import get_settings
from app.cost_tracker import is_killed_today
from app.db import session_scope
from app.line_client import LineClient, ReplyMessage
from app.models import User
from app.personas import get_persona
from app.rate_limiter import RateLimitDecision, check_and_increment
from app.replies import (
    CLAUDE_ERROR,
    COOLDOWN_DAY,
    COOLDOWN_HOUR,
    HINT_SELECT_PERSONA,
    KILLED_OFFLINE,
    OWNER_RATE_LIMIT_ALERT,
    PERSONA_SELECT,
    WELCOME_FOLLOW,
    WELCOME_FOLLOW_QUICK_REPLIES,
)


def handle_event(
    event: dict[str, Any], *, line_client: LineClient, rich_menu_id: str | None
) -> None:
    et = event.get("type")
    if et == "follow":
        _handle_follow(event, line_client, rich_menu_id)
    elif et == "message" and event.get("message", {}).get("type") == "text":
        _handle_message(event, line_client)


def _handle_follow(
    event: dict[str, Any], line_client: LineClient, rich_menu_id: str | None
) -> None:
    user_id = event["source"]["userId"]
    reply_token = event["replyToken"]
    display_name = line_client.get_display_name(user_id)

    with session_scope() as s:
        user = s.get(User, user_id)
        if user is None:
            user = User(
                line_user_id=user_id,
                display_name=display_name,
                current_agent_key=None,
                is_blocked=False,
            )
            s.add(user)
        else:
            user.is_blocked = False
            user.current_agent_key = None
            if display_name:
                user.display_name = display_name

    if rich_menu_id:
        with contextlib.suppress(Exception):
            line_client.link_rich_menu_to_user(line_user_id=user_id, rich_menu_id=rich_menu_id)

    line_client.reply(
        reply_token=reply_token,
        messages=[ReplyMessage.text(WELCOME_FOLLOW, quick_replies=WELCOME_FOLLOW_QUICK_REPLIES)],
    )


def _handle_message(event: dict[str, Any], line_client: LineClient) -> None:
    settings = get_settings()
    user_id = event["source"]["userId"]
    reply_token = event["replyToken"]
    text = event["message"]["text"]

    with session_scope() as s:
        user = s.get(User, user_id)
        if user is None:
            user = User(line_user_id=user_id, current_agent_key=None)
            s.add(user)
            s.flush()
        if user.is_blocked:
            return
        current_agent = user.current_agent_key

    if text in PERSONA_SELECT:
        agent_key = PERSONA_SELECT[text]
        with session_scope() as s:
            user = s.get(User, user_id)
            if user:
                user.current_agent_key = agent_key
        persona = get_persona(agent_key)
        line_client.reply(
            reply_token=reply_token,
            messages=[
                ReplyMessage.text(persona.welcome_message, quick_replies=persona.quick_replies)
            ],
        )
        return

    if current_agent is None:
        line_client.reply(
            reply_token=reply_token,
            messages=[
                ReplyMessage.text(
                    HINT_SELECT_PERSONA, quick_replies=WELCOME_FOLLOW_QUICK_REPLIES
                )
            ],
        )
        return

    if is_killed_today():
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(KILLED_OFFLINE)])
        return

    decision = check_and_increment(
        user_id,
        hour_limit=settings.rate_limit_hour,
        day_limit=settings.rate_limit_day,
    )
    if decision == RateLimitDecision.BLOCKED_HOUR:
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(COOLDOWN_HOUR)])
        return
    if decision == RateLimitDecision.BLOCKED_DAY:
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(COOLDOWN_DAY)])
        return

    try:
        reply = generate_agent_reply(
            line_user_id=user_id, text=text, history_turns=settings.history_turns
        )
    except RateLimitError:
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(CLAUDE_ERROR)])
        _notify_owner_rate_limited(line_client, settings.owner_line_user_id)
        return
    except Exception:
        logging.exception("agent reply failed for user=%s", user_id)
        line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(CLAUDE_ERROR)])
        return

    line_client.reply(reply_token=reply_token, messages=[ReplyMessage.text(reply.text)])


def _notify_owner_rate_limited(line_client: LineClient, owner_line_user_id: str | None) -> None:
    if not owner_line_user_id:
        return
    with contextlib.suppress(Exception):
        line_client.push(
            line_user_id=owner_line_user_id,
            messages=[ReplyMessage.text(OWNER_RATE_LIMIT_ALERT)],
        )
