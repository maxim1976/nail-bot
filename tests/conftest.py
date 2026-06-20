from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

if "DOCKER_HOST" not in os.environ:
    _colima_sock = Path.home() / ".colima" / "default" / "docker.sock"
    if _colima_sock.exists() and not Path("/var/run/docker.sock").exists():
        os.environ["DOCKER_HOST"] = f"unix://{_colima_sock}"

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine") as pg:
        raw = pg.get_connection_url()
        url = raw.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        yield url


@pytest.fixture(scope="session")
def engine(pg_url: str) -> Engine:
    return create_engine(pg_url, future=True)


@pytest.fixture(scope="session", autouse=True)
def _stub_required_env(pg_url: str) -> None:
    from app.config import Settings, get_settings

    Settings.model_config["env_file"] = None

    os.environ.setdefault("LINE_CHANNEL_SECRET", "test-secret")
    os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", pg_url)
    os.environ.setdefault("SELLER_LINE_ID", "@test-seller")
    os.environ.setdefault("ADMIN_JWT_SECRET", "test-jwt-secret-32-chars-minimum!")
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _clean_db(engine: Engine) -> Iterator[None]:
    import app.models  # noqa: F401 — registers models with Base
    from app.db import Base, _engine_for_tests

    _engine_for_tests(engine)
    Base.metadata.create_all(engine)
    yield
    with engine.begin() as conn:
        for tbl in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{tbl.name}" CASCADE'))
