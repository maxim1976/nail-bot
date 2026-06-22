from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin.appointments import router as admin_appointments_router
from app.admin.auth import router as admin_auth_router
from app.admin.portfolio import router as admin_portfolio_router
from app.admin.services import router as admin_services_router
from app.admin.studio import router as admin_studio_router
from app.api.appointments import router as appointments_router
from app.api.portfolio import router as portfolio_router
from app.api.services import router as services_router
from app.config import get_settings
from app.line_client import LineClient
from app.webhook import router as webhook_router


def _build_line_client() -> LineClient:
    return LineClient(channel_access_token=get_settings().line_channel_access_token)


def _rich_menu_id() -> str | None:
    return os.environ.get("RICH_MENU_ID") or None


def create_app() -> FastAPI:
    app = FastAPI(title="Nail Bot — Hualienvibe")

    # Add CORS (LIFF runs from LINE's origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(webhook_router)
    app.include_router(services_router)
    app.include_router(appointments_router)
    app.include_router(portfolio_router)
    app.include_router(admin_auth_router)
    app.include_router(admin_studio_router)
    app.include_router(admin_services_router)
    app.include_router(admin_portfolio_router)
    app.include_router(admin_appointments_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    _liff_dist = Path(__file__).parent.parent / "frontend" / "liff" / "dist"
    if _liff_dist.exists():
        app.mount("/liff", StaticFiles(directory=_liff_dist, html=True), name="liff")

    return app


app = create_app()
