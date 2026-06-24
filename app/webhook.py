from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.line_client import verify_signature

router = APIRouter()


def _run_dispatch(events: list[dict[str, Any]]) -> None:
    from app.event_router import handle_event
    from app.main import _build_line_client, _rich_menu_id

    line_client = _build_line_client()
    rich_menu_id = _rich_menu_id()
    for ev in events:
        try:
            handle_event(ev, line_client=line_client, rich_menu_id=rich_menu_id)
        except Exception:
            logging.exception("event handler failed for event=%s", ev.get("type"))


@router.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature: str | None = Header(default=None),
) -> dict[str, bool]:
    body = await request.body()
    settings = get_settings()
    if not verify_signature(
        secret=settings.line_channel_secret, body=body, header_signature=x_line_signature
    ):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = json.loads(body.decode() or "{}")
    background_tasks.add_task(run_in_threadpool, _run_dispatch, payload.get("events", []))
    return {"ok": True}
