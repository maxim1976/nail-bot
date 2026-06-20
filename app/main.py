from __future__ import annotations

import os

from fastapi import FastAPI

from app.config import get_settings
from app.line_client import LineClient
from app.webhook import router as webhook_router


def _build_line_client() -> LineClient:
    return LineClient(channel_access_token=get_settings().line_channel_access_token)


def _rich_menu_id() -> str | None:
    return os.environ.get("RICH_MENU_ID") or None


def create_app() -> FastAPI:
    app = FastAPI(title="Nail Bot — Hualienvibe")
    app.include_router(webhook_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
