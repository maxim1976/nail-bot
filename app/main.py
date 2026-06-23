from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.admin.appointments import router as admin_appointments_router
from app.admin.auth import router as admin_auth_router
from app.admin.portfolio import router as admin_portfolio_router
from app.admin.schedule import router as admin_schedule_router
from app.admin.services import router as admin_services_router
from app.admin.studio import router as admin_studio_router
from app.api.appointments import router as appointments_router
from app.api.portfolio import router as portfolio_router
from app.api.services import router as services_router
from app.config import get_settings
from app.line_client import LineClient
from app.webhook import router as webhook_router

_RICH_MENU_IMAGE = Path(__file__).parent / "assets" / "rich-menu.jpg"
_rich_menu_id_cache: str | None = None


def _build_line_client() -> LineClient:
    return LineClient(channel_access_token=get_settings().line_channel_access_token)


def _rich_menu_id() -> str | None:
    return _rich_menu_id_cache or get_settings().rich_menu_id or None


def _ensure_rich_menu() -> None:
    global _rich_menu_id_cache
    settings = get_settings()

    # Fast path: already resolved this session
    if _rich_menu_id_cache:
        return

    # If no LIFF ID, rich menu booking button would be broken — skip
    if not settings.liff_id:
        logging.warning("rich menu setup skipped: LIFF_ID not set")
        return

    client = _build_line_client()

    # Use env-configured ID if provided; still set as default to stay consistent
    if settings.rich_menu_id:
        try:
            client.set_default_rich_menu(settings.rich_menu_id)
            _rich_menu_id_cache = settings.rich_menu_id
            return
        except Exception:
            logging.warning("RICH_MENU_ID=%s is invalid (400); will recreate", settings.rich_menu_id)

    # Check if we already created one in a previous deploy
    try:
        existing = client.list_rich_menus()
    except Exception:
        logging.exception("could not list rich menus")
        return

    for menu in existing:
        if menu.get("name") == "Hualienvibe Main Menu":
            rid: str = menu["richMenuId"]
            try:
                client.set_default_rich_menu(rid)
                _rich_menu_id_cache = rid
                logging.info("rich menu reused: %s — set RICH_MENU_ID=%s in env to skip this step", rid, rid)
                return
            except Exception:
                logging.warning("existing menu %s has no image; deleting and recreating", rid)
                try:
                    client.delete_rich_menu(rid)
                except Exception:
                    pass

    # Create from bundled image
    if not _RICH_MENU_IMAGE.exists():
        logging.warning("rich menu image missing at %s — skipping setup", _RICH_MENU_IMAGE)
        return

    try:
        rid = client.create_rich_menu(liff_id=settings.liff_id, image_path=_RICH_MENU_IMAGE)
        client.set_default_rich_menu(rid)
        _rich_menu_id_cache = rid
        logging.info("rich menu created: %s — set RICH_MENU_ID=%s in env to skip this step", rid, rid)
    except Exception:
        logging.exception("rich menu creation failed")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    import asyncio
    from app.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    await asyncio.to_thread(_ensure_rich_menu)
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(title="Nail Bot — Hualienvibe", lifespan=_lifespan)

    # Add CORS (LIFF runs from LINE's origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
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
    app.include_router(admin_schedule_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    _liff_dist = Path(__file__).parent.parent / "frontend" / "liff" / "dist"
    if _liff_dist.exists():
        app.mount("/liff", StaticFiles(directory=_liff_dist, html=True), name="liff")

    _admin_ui = Path(__file__).parent.parent / "frontend" / "admin"
    if _admin_ui.exists():
        app.mount("/dashboard", StaticFiles(directory=_admin_ui, html=True), name="admin_ui")

    _landing = Path(__file__).parent / "assets" / "landing"
    if _landing.exists():
        app.mount("/uploads", StaticFiles(directory=_landing / "uploads"), name="landing_uploads")

        @app.get("/")
        async def landing_page() -> FileResponse:
            return FileResponse(_landing / "index.html")

    return app


app = create_app()
