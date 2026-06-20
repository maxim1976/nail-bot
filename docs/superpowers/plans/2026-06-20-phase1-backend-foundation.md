# Phase 1: Backend Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the nail-bot project with all DB models, a working LINE webhook, both AI personas (booking_assistant and sales_agent), language detection, rate limiting, and cost tracking — so the bot can be connected to LINE and have real conversations.

**Architecture:** FastAPI app with a synchronous SQLAlchemy session pattern (same as bento-bot). LINE webhook receives events, event_router dispatches follow/message events, agent_service calls Claude with the appropriate persona system prompt, and replies are sent via LineClient. Language is auto-detected by Claude using a `[LANG:xx]` sentinel in responses.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (sync), psycopg 3, Alembic, Anthropic SDK, httpx, pydantic-settings, pytest + testcontainers[postgres], ruff.

## Global Constraints

- Python `>=3.12,<3.13` — use `from __future__ import annotations` where needed for forward refs
- All DB changes go through Alembic — never edit migration files by hand
- TDD: write the failing test first, run to confirm failure, then implement
- Commits go directly to `master` — no feature branches
- Line length: 100 (ruff enforced)
- Model: `claude-sonnet-4-6` (not haiku — nail-bot uses Sonnet)
- Pricing: Sonnet 4.6 — input $3/Mtok, output $15/Mtok, cache_read $0.30/Mtok, cache_write $3.75/Mtok
- Follow bento-bot patterns exactly unless this plan says otherwise

---

## File Map

```
nail-bot/
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── line_client.py
│   ├── anthropic_client.py
│   ├── cost_tracker.py
│   ├── rate_limiter.py
│   ├── agent_service.py
│   ├── replies.py
│   ├── event_router.py
│   ├── webhook.py
│   ├── main.py
│   └── personas/
│       ├── __init__.py
│       ├── _base.py
│       ├── _shared.py
│       ├── booking_assistant.py
│       └── sales_agent.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_line_client.py
    ├── test_event_router.py
    └── test_webhook.py
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `Dockerfile`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `app/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: `get_settings()` is importable; `pytest` runs without errors; `alembic` CLI is available

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "nail-bot"
version = "0.1.0"
description = "Hualienvibe — LINE nail booking bot"
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "SQLAlchemy>=2.0.36",
    "psycopg[binary]>=3.2",
    "alembic>=1.14",
    "anthropic>=0.42",
    "httpx>=0.27",
    "pyjwt>=2.9",
    "bcrypt>=4.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "testcontainers[postgres]>=4.8",
    "freezegun>=1.5",
    "respx>=0.21",
    "ruff>=0.7",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `.env.example`**

```ini
LINE_CHANNEL_SECRET=your_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here

ANTHROPIC_API_KEY=sk-ant-...

DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/nailbot

OWNER_LINE_USER_ID=Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SELLER_LINE_ID=@hualienvibe
RICH_MENU_ID=

ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
ADMIN_JWT_SECRET=change-me-32-chars-minimum-secret
ADMIN_BASE_URL=http://localhost:8000

RATE_LIMIT_HOUR=10
RATE_LIMIT_DAY=30
HISTORY_TURNS=20
DAILY_COST_CEILING_USD=5.0
```

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
.venv/
dist/
*.egg-info/
.ruff_cache/
.pytest_cache/
node_modules/
frontend/liff/dist/
frontend/admin/dist/
.DS_Store
```

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1.7

# ── Stage 1: build frontends (skipped in Phase 1 — no frontend yet) ──────────
# Placeholder — frontend stages will be added in Phase 2/3

# ── Stage 2: Python runtime ───────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir -U pip
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

- [ ] **Step 5: Create `alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = driver://user:pass@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 6: Create `alembic/env.py`**

```python
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import app.models  # noqa: F401, E402 — registers all models
from app.db import Base  # noqa: E402

target_metadata = Base.metadata


def _get_url() -> str:
    import os
    url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    if url and url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    if url and url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Create empty `app/__init__.py` and `tests/__init__.py`**

Both files are empty. Just create them.

- [ ] **Step 8: Set up virtualenv and install dependencies**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: no errors, `pytest --collect-only` shows 0 tests collected.

- [ ] **Step 9: Commit**

```bash
git init
git add pyproject.toml .env.example .gitignore Dockerfile alembic.ini alembic/env.py app/__init__.py tests/__init__.py
git commit -m "chore: project scaffold — nail-bot phase 1"
```

---

### Task 2: Config + DB

**Files:**
- Create: `app/config.py`
- Create: `app/db.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`, `session_scope() -> Iterator[Session]`, `Base`, `_engine_for_tests(engine)`

- [ ] **Step 1: Create `app/config.py`**

```python
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    line_channel_secret: str
    line_channel_access_token: str

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    daily_cost_ceiling_usd: float = 5.0
    rate_limit_hour: int = 10
    rate_limit_day: int = 30
    history_turns: int = 20

    owner_line_user_id: str | None = None
    seller_line_id: str = ""
    rich_menu_id: str | None = None

    liff_id: str = ""

    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_jwt_secret: str = ""
    admin_base_url: str = "http://localhost:8000"

    database_url: str
    port: int = 8000

    @field_validator("database_url", mode="after")
    @classmethod
    def _ensure_psycopg_driver(cls, raw: str) -> str:
        if raw.startswith("postgres://"):
            return "postgresql+psycopg://" + raw[len("postgres://"):]
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return "postgresql+psycopg://" + raw[len("postgresql://"):]
        return raw


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 2: Create `app/db.py`**

```python
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _engine_for_tests(engine: Engine) -> None:
    global _engine, _SessionLocal
    if _engine is not None and _engine is not engine:
        _engine.dispose()
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(get_settings().database_url, future=True, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def _session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py app/db.py
git commit -m "feat: config + db session scope"
```

---

### Task 3: Data Models

**Files:**
- Create: `app/models.py`

**Interfaces:**
- Produces: `User`, `Conversation`, `Message`, `UsageCounter`, `DailyCost`, `StudioProfile`, `Service`, `WeeklyTemplate`, `DateOverride`, `Appointment`, `PortfolioItem` — all importable from `app.models`

- [ ] **Step 1: Write `app/models.py`**

```python
from __future__ import annotations

import uuid
from datetime import date as dt_date
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    line_user_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    current_agent_key: Mapped[str | None] = mapped_column(String)
    preferred_language: Mapped[str] = mapped_column(
        String, nullable=False, default="zh", server_default="zh"
    )
    followed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("line_user_id", "agent_key", name="uq_user_agent"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    agent_key: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conv_created", "conversation_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (PrimaryKeyConstraint("line_user_id", "window_kind", "window_start"),)

    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    window_kind: Mapped[str] = mapped_column(String, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class DailyCost(Base):
    __tablename__ = "daily_cost"

    date: Mapped[dt_date] = mapped_column(Date, primary_key=True)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    killed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class StudioProfile(Base):
    """Singleton row (id=1). All nail tech studio metadata for the AI and admin."""
    __tablename__ = "studio_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    studio_name: Mapped[str] = mapped_column(String, nullable=False, server_default="Hualienvibe")
    owner_name: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    instagram: Mapped[str | None] = mapped_column(String)
    cancellation_policy: Mapped[str | None] = mapped_column(String)
    aftercare_notes: Mapped[str | None] = mapped_column(String)
    ai_persona_notes: Mapped[str | None] = mapped_column(String)
    owner_line_user_id: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_en: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_tl: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_id: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    name_vi: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    description: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    agent_notes: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, nullable=False, server_default="general")
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    in_carousel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appointments: Mapped[list[Appointment]] = relationship(back_populates="service")
    portfolio_items: Mapped[list[PortfolioItem]] = relationship(back_populates="service")


class WeeklyTemplate(Base):
    """One row per active day of week. dow: 0=Mon … 6=Sun."""
    __tablename__ = "weekly_template"

    dow: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class DateOverride(Base):
    """Block a specific date or override its hours."""
    __tablename__ = "date_overrides"

    date: Mapped[dt_date] = mapped_column(Date, primary_key=True)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    custom_start: Mapped[time | None] = mapped_column(Time)
    custom_end: Mapped[time | None] = mapped_column(Time)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.line_user_id"), nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    # status: confirmed → completed | cancelled (auto-confirmed on booking)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="confirmed", server_default="confirmed"
    )
    customer_name: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    notes: Mapped[str | None] = mapped_column(String)
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service: Mapped[Service] = relationship(back_populates="appointments")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, server_default="")
    image_url: Mapped[str] = mapped_column(String, nullable=False)
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    service: Mapped[Service | None] = relationship(back_populates="portfolio_items")
```

- [ ] **Step 2: Commit**

```bash
git add app/models.py
git commit -m "feat: all data models (User, Service, Appointment, WeeklyTemplate, etc.)"
```

---

### Task 4: Initial Alembic Migration

**Files:**
- Create: `alembic/versions/0001_initial.py`

**Interfaces:**
- Produces: all tables exist in DB after `alembic upgrade head`

- [ ] **Step 1: Generate migration**

```bash
alembic revision --autogenerate -m "initial"
```

Expected: creates `alembic/versions/<hash>_initial.py`. Rename it to `0001_initial.py` and update `revision` and `down_revision` accordingly.

- [ ] **Step 2: Inspect the generated file**

Open the generated file and verify it contains `CREATE TABLE` statements for: `users`, `conversations`, `messages`, `usage_counters`, `daily_cost`, `studio_profile`, `services`, `weekly_template`, `date_overrides`, `appointments`, `portfolio_items`. All 11 tables must be present.

- [ ] **Step 3: Run migration against a local database**

```bash
# Requires a running Postgres instance with DATABASE_URL set in .env
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial` — no errors.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat: initial alembic migration — all 11 tables"
```

---

### Task 5: Test Infrastructure

**Files:**
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `engine` fixture (real Postgres via testcontainers), `_stub_required_env` fixture, `_clean_db` fixture (creates + truncates tables between tests)

- [ ] **Step 1: Verify Docker is running**

```bash
docker info
```

Expected: Docker daemon info printed. If using Colima: `colima start` first.

- [ ] **Step 2: Create `tests/conftest.py`**

```python
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
```

- [ ] **Step 3: Run tests to verify infra works**

```bash
pytest --collect-only
```

Expected: `0 items / 0 errors` — no collection errors.

```bash
pytest -x
```

Expected: `no tests ran` — infrastructure runs cleanly with no errors.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: testcontainers postgres test infrastructure"
```

---

### Task 6: LINE Client

**Files:**
- Create: `app/line_client.py`
- Create: `tests/test_line_client.py`

**Interfaces:**
- Produces: `verify_signature(*, secret, body, header_signature) -> bool`, `ReplyMessage.text(body, *, quick_replies) -> ReplyMessage`, `ReplyMessage.flex(alt_text, contents) -> ReplyMessage`, `LineClient(*, channel_access_token)` with `.reply()`, `.push()`, `.multicast()`, `.link_rich_menu_to_user()`, `.get_display_name()`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_line_client.py
from __future__ import annotations

import base64
import hashlib
import hmac

import pytest
import respx
import httpx

from app.line_client import LineClient, ReplyMessage, verify_signature


def _make_sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def test_verify_signature_valid():
    body = b'{"events":[]}'
    sig = _make_sig("mysecret", body)
    assert verify_signature(secret="mysecret", body=body, header_signature=sig) is True


def test_verify_signature_invalid():
    body = b'{"events":[]}'
    assert verify_signature(secret="mysecret", body=body, header_signature="bad") is False


def test_verify_signature_missing():
    assert verify_signature(secret="s", body=b"b", header_signature=None) is False


def test_reply_message_text_no_quick_replies():
    msg = ReplyMessage.text("hello")
    assert msg.payload == {"type": "text", "text": "hello"}


def test_reply_message_text_with_quick_replies():
    msg = ReplyMessage.text("choose", quick_replies=("A", "B"))
    assert msg.payload["quickReply"]["items"][0]["action"]["label"] == "A"
    assert msg.payload["quickReply"]["items"][1]["action"]["label"] == "B"


def test_reply_message_flex():
    contents = {"type": "bubble"}
    msg = ReplyMessage.flex("alt", contents)
    assert msg.payload == {"type": "flex", "altText": "alt", "contents": contents}


@respx.mock
def test_line_client_reply():
    route = respx.post("https://api.line.me/v2/bot/message/reply").mock(
        return_value=httpx.Response(200, json={})
    )
    client = LineClient(channel_access_token="tok")
    client.reply(reply_token="rt", messages=[ReplyMessage.text("hi")])
    assert route.called


@respx.mock
def test_line_client_push():
    route = respx.post("https://api.line.me/v2/bot/message/push").mock(
        return_value=httpx.Response(200, json={})
    )
    client = LineClient(channel_access_token="tok")
    client.push(line_user_id="U123", messages=[ReplyMessage.text("hi")])
    assert route.called


@respx.mock
def test_line_client_get_display_name_ok():
    respx.get("https://api.line.me/v2/bot/profile/U123").mock(
        return_value=httpx.Response(200, json={"displayName": "Alice"})
    )
    client = LineClient(channel_access_token="tok")
    assert client.get_display_name("U123") == "Alice"


@respx.mock
def test_line_client_get_display_name_404():
    respx.get("https://api.line.me/v2/bot/profile/U999").mock(
        return_value=httpx.Response(404, json={})
    )
    client = LineClient(channel_access_token="tok")
    assert client.get_display_name("U999") is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_line_client.py -v
```

Expected: `ImportError: cannot import name 'LineClient' from 'app.line_client'`

- [ ] **Step 3: Create `app/line_client.py`**

```python
from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

import httpx


def verify_signature(*, secret: str, body: bytes, header_signature: str | None) -> bool:
    if not header_signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, header_signature)


@dataclass(frozen=True)
class ReplyMessage:
    payload: dict[str, Any]

    @classmethod
    def text(cls, body: str, *, quick_replies: tuple[str, ...] = ()) -> ReplyMessage:
        msg: dict[str, Any] = {"type": "text", "text": body}
        if quick_replies:
            msg["quickReply"] = {
                "items": [
                    {"type": "action", "action": {"type": "message", "label": qr, "text": qr}}
                    for qr in quick_replies
                ]
            }
        return cls(payload=msg)

    @classmethod
    def flex(cls, alt_text: str, contents: dict[str, Any]) -> ReplyMessage:
        return cls(payload={"type": "flex", "altText": alt_text, "contents": contents})


class LineClient:
    BASE = "https://api.line.me/v2/bot"

    def __init__(self, *, channel_access_token: str, timeout: float = 10.0) -> None:
        self._token = channel_access_token
        self._http = httpx.Client(
            timeout=timeout, headers={"Authorization": f"Bearer {channel_access_token}"}
        )

    def reply(self, *, reply_token: str, messages: list[ReplyMessage]) -> None:
        body = {"replyToken": reply_token, "messages": [m.payload for m in messages]}
        r = self._http.post(f"{self.BASE}/message/reply", json=body)
        r.raise_for_status()

    def push(self, *, line_user_id: str, messages: list[ReplyMessage]) -> None:
        body = {"to": line_user_id, "messages": [m.payload for m in messages]}
        r = self._http.post(f"{self.BASE}/message/push", json=body)
        r.raise_for_status()

    def multicast(self, *, user_ids: list[str], messages: list[ReplyMessage]) -> None:
        for i in range(0, len(user_ids), 500):
            chunk = user_ids[i: i + 500]
            body = {"to": chunk, "messages": [m.payload for m in messages]}
            r = self._http.post(f"{self.BASE}/message/multicast", json=body)
            r.raise_for_status()

    def link_rich_menu_to_user(self, *, line_user_id: str, rich_menu_id: str) -> None:
        r = self._http.post(f"{self.BASE}/user/{line_user_id}/richmenu/{rich_menu_id}")
        r.raise_for_status()

    def get_display_name(self, line_user_id: str) -> str | None:
        try:
            r = self._http.get(f"{self.BASE}/profile/{line_user_id}")
            if r.status_code != 200:
                return None
            return r.json().get("displayName")
        except httpx.HTTPError:
            return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_line_client.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/line_client.py tests/test_line_client.py
git commit -m "feat: LINE client — verify_signature, ReplyMessage, LineClient"
```

---

### Task 7: Anthropic Client + Cost Tracker + Rate Limiter

**Files:**
- Create: `app/anthropic_client.py`
- Create: `app/cost_tracker.py`
- Create: `app/rate_limiter.py`

**Interfaces:**
- Produces: `call_claude(*, system_prompt, history, user_message, model, max_tokens) -> AnthropicCallResult`, `record_call(c, *, ceiling_usd) -> float`, `is_killed_today() -> bool`, `check_and_increment(line_user_id, *, hour_limit, day_limit) -> RateLimitDecision`

- [ ] **Step 1: Create `app/anthropic_client.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

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
```

- [ ] **Step 2: Create `app/cost_tracker.py`**

Sonnet 4.6 pricing: input $3/Mtok, output $15/Mtok, cache_read $0.30/Mtok, cache_write $3.75/Mtok.

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import session_scope
from app.models import DailyCost


@dataclass(frozen=True)
class SonnetPricing:
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float
    cache_write_per_mtok: float


SONNET_PRICING = SonnetPricing(
    input_per_mtok=3.00,
    output_per_mtok=15.00,
    cache_read_per_mtok=0.30,
    cache_write_per_mtok=3.75,
)


@dataclass(frozen=True)
class UsageCounts:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int


def price_call(c: UsageCounts) -> float:
    p = SONNET_PRICING
    return (
        c.input_tokens / 1_000_000 * p.input_per_mtok
        + c.output_tokens / 1_000_000 * p.output_per_mtok
        + c.cache_read_tokens / 1_000_000 * p.cache_read_per_mtok
        + c.cache_write_tokens / 1_000_000 * p.cache_write_per_mtok
    )


def _today() -> date:
    return datetime.now(UTC).date()


def record_call(c: UsageCounts, *, ceiling_usd: float) -> float:
    cost = price_call(c)
    today = _today()
    with session_scope() as s:
        ins = pg_insert(DailyCost).values(
            date=today, total_cost_usd=Decimal(str(cost)), killed=False
        )
        ins = ins.on_conflict_do_update(
            index_elements=["date"],
            set_={"total_cost_usd": DailyCost.total_cost_usd + Decimal(str(cost))},
        )
        s.execute(ins)
        row = s.get(DailyCost, today)
        if row is not None and float(row.total_cost_usd) >= ceiling_usd and not row.killed:
            row.killed = True
    return cost


def is_killed_today() -> bool:
    today = _today()
    with session_scope() as s:
        row = s.execute(select(DailyCost).where(DailyCost.date == today)).scalar_one_or_none()
        return bool(row and row.killed)
```

- [ ] **Step 3: Create `app/rate_limiter.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import session_scope
from app.models import UsageCounter


class RateLimitDecision(StrEnum):
    OK = "ok"
    BLOCKED_HOUR = "blocked_hour"
    BLOCKED_DAY = "blocked_day"


def _hour_bucket(now: datetime) -> datetime:
    minute_floor = (now.minute // 10) * 10
    return now.replace(minute=minute_floor, second=0, microsecond=0)


def _day_bucket(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def check_and_increment(
    line_user_id: str, *, hour_limit: int, day_limit: int
) -> RateLimitDecision:
    now = datetime.now(UTC)
    hour_floor = now - timedelta(hours=1)
    day_floor = now - timedelta(hours=24)

    with session_scope() as s:
        hour_count = (
            s.scalar(
                select(func.coalesce(func.sum(UsageCounter.message_count), 0)).where(
                    UsageCounter.line_user_id == line_user_id,
                    UsageCounter.window_kind == "hour",
                    UsageCounter.window_start > hour_floor,
                )
            )
            or 0
        )
        if hour_count >= hour_limit:
            return RateLimitDecision.BLOCKED_HOUR

        day_count = (
            s.scalar(
                select(func.coalesce(func.sum(UsageCounter.message_count), 0)).where(
                    UsageCounter.line_user_id == line_user_id,
                    UsageCounter.window_kind == "day",
                    UsageCounter.window_start > day_floor,
                )
            )
            or 0
        )
        if day_count >= day_limit:
            return RateLimitDecision.BLOCKED_DAY

        for kind, bucket in (("hour", _hour_bucket(now)), ("day", _day_bucket(now))):
            stmt = (
                pg_insert(UsageCounter)
                .values(
                    line_user_id=line_user_id,
                    window_kind=kind,
                    window_start=bucket,
                    message_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["line_user_id", "window_kind", "window_start"],
                    set_={"message_count": UsageCounter.message_count + 1},
                )
            )
            s.execute(stmt)

        return RateLimitDecision.OK
```

- [ ] **Step 4: Commit**

```bash
git add app/anthropic_client.py app/cost_tracker.py app/rate_limiter.py
git commit -m "feat: anthropic client, cost tracker (Sonnet pricing), rate limiter"
```

---

### Task 8: Personas

**Files:**
- Create: `app/personas/__init__.py`
- Create: `app/personas/_base.py`
- Create: `app/personas/_shared.py`
- Create: `app/personas/booking_assistant.py`
- Create: `app/personas/sales_agent.py`

**Interfaces:**
- Produces: `get_persona(key) -> Persona`, `system_prompt_for(key, **context) -> str`, `booking_assistant.persona`, `sales_agent.persona`

- [ ] **Step 1: Create `app/personas/_base.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    key: str
    display_name: str
    welcome_message: str
    quick_replies: tuple[str, ...]
    body_prompt: str
```

- [ ] **Step 2: Create `app/personas/_shared.py`**

```python
SHARED_FOOTER = """
[共通規範]

身份: 你是 AI 助理。若被問是否為 AI，誠實回答是 AI 助理，不要假裝是真人。

安全: 拒絕非法行為、誹謗、成人內容。語氣保持親切專業。

格式: 一般對話每則回覆控制在 200 字以內。如需列出服務清單時可加長。
""".strip()


def compose_system_prompt(body: str) -> str:
    return f"{body.strip()}\n\n{SHARED_FOOTER}"
```

- [ ] **Step 3: Create `app/personas/booking_assistant.py`**

The `{studio_section}`, `{services_section}`, `{preferred_language}` placeholders are filled by `agent_service.py` at runtime.

```python
from app.personas._base import Persona

_BODY = """\
You are the friendly AI booking assistant for {studio_name} — a home-visit nail art service.

STUDIO INFO:
{studio_section}

SERVICES:
{services_section}

YOUR ROLE:
- Answer questions about services, pricing, aftercare, and studio policies
- Guide customers to the booking menu (tap 預約 below) for scheduling
- Help customers view or cancel their existing appointments
- Always respond in the customer's language

LANGUAGE:
The customer's current preferred language is: {preferred_language}
(zh=繁體中文, en=English, tl=Tagalog, id=Bahasa Indonesia, vi=Tiếng Việt)
If the customer writes in a different language, start your reply with [LANG:xx]
(e.g. [LANG:en]) where xx is the detected language code, then reply in their language.

BOUNDARIES:
- You cannot complete bookings yourself — always direct to the LIFF booking menu
- Keep replies under 200 characters for simple questions; longer is fine for service lists
""".strip()

persona = Persona(
    key="booking_assistant",
    display_name="預約助理",
    welcome_message=(
        "您好！我是您的美甲預約助理 💅\n"
        "可以幫您介紹服務、查詢預約，或回答任何問題！\n"
        "想預約請點下方選單的「預約」按鈕 👇"
    ),
    quick_replies=("💼 服務項目", "📅 我的預約", "📍 聯絡方式", "🌐 語言切換"),
    body_prompt=_BODY,
)
```

- [ ] **Step 4: Create `app/personas/sales_agent.py`**

The `{seller_line_id}` placeholder is filled by `agent_service.py` from `settings.seller_line_id`.

```python
from app.personas._base import Persona

_BODY = """\
You are the demo assistant for Hualienvibe — a LINE-based booking system built specifically
for home-visit nail technicians (美甲到府) in Taiwan. You are speaking to a potential buyer
who is a nail technician curious about automating her booking process.

PRODUCT: Hualienvibe LINE Bot System
PRICE: NT$18,000+ (customisation scope discussed on inquiry)
DELIVERY: 3–7 business days after deposit confirmed
CONTACT: To purchase or inquire → LINE: {seller_line_id}

WHAT THE SYSTEM INCLUDES:
1. LINE Bot Integration — customers book inside LINE, no app download needed
2. AI Booking Assistant — handles FAQ, guides booking, reschedule & cancel in 5 languages
   (繁體中文 / English / Tagalog / Bahasa Indonesia / Tiếng Việt)
3. Smart Slot Picker — LIFF mini-app: pick service → pick date → pick time → confirm
4. Portfolio Gallery — nail art showcase in LINE chat carousel + full LIFF gallery page
5. Admin Dashboard — manage schedule, services, portfolio, appointments, studio profile
6. Automatic Notifications — booking confirmation + 24h reminder to customers,
   daily morning appointment summary to the nail tech
7. Cost Control — rate limiting and daily AI spend ceiling built in

WHO IS THIS FOR:
Home-visit nail technicians in Taiwan who want to stop managing bookings manually
via LINE messages and want to reduce no-shows with automatic reminders.

LANGUAGE DETECTION:
Always respond in the same language the potential buyer writes in.
If they switch languages, switch with them.
If you detect a language change, start your reply with [LANG:xx]
(zh/en/tl/id/vi), then respond in the new language.

GUIDELINES:
- Be warm, enthusiastic, and honest about what the system does
- Answer technical questions clearly (how AI works, what happens on booking, etc.)
- Always close with an invitation to contact {seller_line_id} on LINE to get started
""".strip()

persona = Persona(
    key="sales_agent",
    display_name="系統介紹",
    welcome_message=(
        "您好！我是 Hualienvibe 的示範助理 🌸\n"
        "想了解這套美甲預約系統嗎？請隨時問我！\n"
        "想了解功能、價格，或準備購買，都可以直接跟我說 😊"
    ),
    quick_replies=("🔧 系統功能", "💰 價格方案", "🕐 多久可上線", "📞 如何購買"),
    body_prompt=_BODY,
)
```

- [ ] **Step 5: Create `app/personas/__init__.py`**

```python
from app.personas._base import Persona
from app.personas._shared import compose_system_prompt
from app.personas import booking_assistant as _ba
from app.personas import sales_agent as _sa

PERSONAS: dict[str, Persona] = {
    _ba.persona.key: _ba.persona,
    _sa.persona.key: _sa.persona,
}


def get_persona(key: str) -> Persona:
    if key not in PERSONAS:
        raise KeyError(f"unknown persona key: {key!r}")
    return PERSONAS[key]


def system_prompt_for(key: str, **context: str) -> str:
    body = get_persona(key).body_prompt
    if context:
        body = body.format(**context)
    return compose_system_prompt(body)


__all__ = ["PERSONAS", "Persona", "get_persona", "system_prompt_for"]
```

- [ ] **Step 6: Commit**

```bash
git add app/personas/
git commit -m "feat: personas — booking_assistant and sales_agent with language detection"
```

---

### Task 9: Agent Service

**Files:**
- Create: `app/agent_service.py`

**Interfaces:**
- Consumes: `call_claude()`, `record_call()`, `system_prompt_for()`, `session_scope()`, `User`, `Conversation`, `Message`, `Service`, `StudioProfile`
- Produces: `generate_agent_reply(*, line_user_id, text, history_turns) -> AgentReply` where `AgentReply` has `.text: str` and `.cost_usd: float`; language detection side-effect: saves `User.preferred_language` if Claude returns a `[LANG:xx]` sentinel

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_service.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_agent_service.py -v
```

Expected: `ImportError: cannot import name 'generate_agent_reply' from 'app.agent_service'`

- [ ] **Step 3: Create `app/agent_service.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select

from app.anthropic_client import AnthropicCallResult, ChatTurn, call_claude
from app.config import get_settings
from app.cost_tracker import record_call
from app.db import session_scope
from app.models import Appointment, Conversation, Message, Service, StudioProfile, User
from app.personas import system_prompt_for

_LANG_SENTINEL = re.compile(r"^\[LANG:([a-z]{2})\]\s*")
_VALID_LANGS = {"zh", "en", "tl", "id", "vi"}


@dataclass(frozen=True)
class AgentReply:
    text: str
    cost_usd: float


def _parse_lang_sentinel(text: str) -> tuple[str | None, str]:
    """Return (detected_lang_or_None, cleaned_text)."""
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
    """Return (studio_name, studio_section, services_section)."""
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


def _build_system_prompt(agent_key: str, preferred_language: str) -> str:
    settings = get_settings()
    if agent_key == "booking_assistant":
        studio_name, studio_section, services_section = _build_studio_section()
        return system_prompt_for(
            agent_key,
            studio_name=studio_name,
            studio_section=studio_section,
            services_section=services_section,
            preferred_language=preferred_language,
        )
    if agent_key == "sales_agent":
        seller_line_id = settings.seller_line_id or "（請洽開發者）"
        return system_prompt_for(agent_key, seller_line_id=seller_line_id, preferred_language=preferred_language)
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

    result: AnthropicCallResult = call_claude(
        system_prompt=system_prompt,
        history=history,
        user_message=text,
        model=settings.anthropic_model,
    )

    detected_lang, clean_text = _parse_lang_sentinel(result.text)
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_agent_service.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/agent_service.py tests/test_agent_service.py
git commit -m "feat: agent service — language sentinel detection, history, cost tracking"
```

---

### Task 10: Replies + Event Router + Webhook + Main

**Files:**
- Create: `app/replies.py`
- Create: `app/event_router.py`
- Create: `app/webhook.py`
- Create: `app/main.py`
- Create: `tests/test_event_router.py`
- Create: `tests/test_webhook.py`

**Interfaces:**
- Consumes: `LineClient`, `verify_signature`, `generate_agent_reply`, `check_and_increment`, `is_killed_today`, `get_persona`, `session_scope`, `User`
- Produces: `POST /webhook` (verified LINE endpoint), `GET /health`

- [ ] **Step 1: Create `app/replies.py`**

```python
# User-facing string constants. All are in Traditional Chinese (default language).
# The AI handles translation for other languages at runtime.

PERSONA_SELECT: dict[str, str] = {
    "💅 我要預約": "booking_assistant",
    "🏪 了解此服務": "sales_agent",
}

WELCOME_FOLLOW = (
    "嗨！歡迎來到 Hualienvibe 💅\n"
    "請問妳是？"
)
WELCOME_FOLLOW_QUICK_REPLIES: tuple[str, ...] = ("💅 我要預約", "🏪 了解此服務")

HINT_SELECT_PERSONA = "請先選擇妳的身份 👇"

COOLDOWN_HOUR = "您傳的訊息有點頻繁，請等 1 小時後再試 🙏"
COOLDOWN_DAY = "您今天的訊息已達上限，請明天再來 🙏"
KILLED_OFFLINE = "系統暫時休息中，請稍後再試 🙏"
CLAUDE_ERROR = "我這邊出了一點狀況，請稍後再試 🙏"

OWNER_RATE_LIMIT_ALERT = (
    "⚠️ Anthropic 429: nail-bot hit account rate limit; users seeing fallback reply."
)
```

- [ ] **Step 2: Write failing tests for the event router**

```python
# tests/test_event_router.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.db import session_scope
from app.event_router import handle_event
from app.models import User


def _line_client() -> MagicMock:
    return MagicMock()


def _follow_event(user_id: str = "U001") -> dict:
    return {
        "type": "follow",
        "replyToken": "rt001",
        "source": {"userId": user_id},
    }


def _message_event(text: str, user_id: str = "U001") -> dict:
    return {
        "type": "message",
        "replyToken": "rt001",
        "source": {"userId": user_id},
        "message": {"type": "text", "text": text},
    }


def test_follow_creates_user_and_replies():
    lc = _line_client()
    lc.get_display_name.return_value = "Alice"
    handle_event(_follow_event(), line_client=lc, rich_menu_id=None)

    with session_scope() as s:
        user = s.get(User, "U001")
    assert user is not None
    assert user.current_agent_key is None  # not set until persona selected
    lc.reply.assert_called_once()
    # welcome message includes both persona quick replies
    call_kwargs = lc.reply.call_args.kwargs
    msg = call_kwargs["messages"][0]
    labels = [i["action"]["label"] for i in msg.payload["quickReply"]["items"]]
    assert "💅 我要預約" in labels
    assert "🏪 了解此服務" in labels


def test_follow_sets_rich_menu():
    lc = _line_client()
    lc.get_display_name.return_value = None
    handle_event(_follow_event(), line_client=lc, rich_menu_id="RM001")
    lc.link_rich_menu_to_user.assert_called_once_with(line_user_id="U001", rich_menu_id="RM001")


def test_persona_selection_booking_assistant():
    with session_scope() as s:
        s.add(User(line_user_id="U001"))
    lc = _line_client()
    handle_event(_message_event("💅 我要預約"), line_client=lc, rich_menu_id=None)
    with session_scope() as s:
        user = s.get(User, "U001")
    assert user.current_agent_key == "booking_assistant"
    lc.reply.assert_called_once()


def test_persona_selection_sales_agent():
    with session_scope() as s:
        s.add(User(line_user_id="U001"))
    lc = _line_client()
    handle_event(_message_event("🏪 了解此服務"), line_client=lc, rich_menu_id=None)
    with session_scope() as s:
        user = s.get(User, "U001")
    assert user.current_agent_key == "sales_agent"


def test_message_without_persona_prompts_selection():
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key=None))
    lc = _line_client()
    handle_event(_message_event("hello"), line_client=lc, rich_menu_id=None)
    lc.reply.assert_called_once()
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "選擇" in msg_text or "身份" in msg_text


@patch("app.event_router.is_killed_today", return_value=True)
def test_killed_system_returns_offline(_):
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "休息" in msg_text


@patch("app.event_router.check_and_increment")
@patch("app.event_router.generate_agent_reply")
def test_rate_limited_hour_returns_cooldown(mock_reply, mock_rate):
    from app.rate_limiter import RateLimitDecision
    mock_rate.return_value = RateLimitDecision.BLOCKED_HOUR
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    mock_reply.assert_not_called()
    msg_text = lc.reply.call_args.kwargs["messages"][0].payload["text"]
    assert "頻繁" in msg_text


@patch("app.event_router.check_and_increment")
@patch("app.event_router.generate_agent_reply")
def test_normal_message_calls_agent(mock_reply, mock_rate):
    from app.agent_service import AgentReply
    from app.rate_limiter import RateLimitDecision
    mock_rate.return_value = RateLimitDecision.OK
    mock_reply.return_value = AgentReply(text="response", cost_usd=0.001)
    with session_scope() as s:
        s.add(User(line_user_id="U001", current_agent_key="booking_assistant"))
    lc = _line_client()
    handle_event(_message_event("hi"), line_client=lc, rich_menu_id=None)
    mock_reply.assert_called_once()
    lc.reply.assert_called_once()
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest tests/test_event_router.py -v
```

Expected: `ImportError: cannot import name 'handle_event' from 'app.event_router'`

- [ ] **Step 4: Create `app/event_router.py`**

```python
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
            user.current_agent_key = None  # reset on re-follow
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

    # Persona selection via quick reply tap
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

    # No persona selected yet
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
```

- [ ] **Step 5: Run event router tests — verify they pass**

```bash
pytest tests/test_event_router.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Write webhook test**

```python
# tests/test_webhook.py
from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _sig(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_webhook_invalid_signature(client: TestClient):
    body = json.dumps({"events": []}).encode()
    r = client.post("/webhook", content=body, headers={"x-line-signature": "bad"})
    assert r.status_code == 401


def test_webhook_valid_signature(client: TestClient):
    import os
    secret = os.environ["LINE_CHANNEL_SECRET"]
    body = json.dumps({"events": []}).encode()
    sig = _sig(secret, body)
    r = client.post("/webhook", content=body, headers={"x-line-signature": sig})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
```

- [ ] **Step 7: Create `app/webhook.py`**

```python
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
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
    request: Request, x_line_signature: str | None = Header(default=None)
) -> dict[str, bool]:
    body = await request.body()
    settings = get_settings()
    if not verify_signature(
        secret=settings.line_channel_secret, body=body, header_signature=x_line_signature
    ):
        raise HTTPException(status_code=401, detail="invalid signature")
    payload = json.loads(body.decode() or "{}")
    await run_in_threadpool(_run_dispatch, payload.get("events", []))
    return {"ok": True}
```

- [ ] **Step 8: Create `app/main.py`**

```python
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
```

- [ ] **Step 9: Run all tests**

```bash
pytest -v
```

Expected: all tests PASS. No failures.

- [ ] **Step 10: Run linter**

```bash
ruff check app/ tests/
```

Expected: no errors. Fix any that appear before committing.

- [ ] **Step 11: Commit**

```bash
git add app/replies.py app/event_router.py app/webhook.py app/main.py \
        tests/test_event_router.py tests/test_webhook.py
git commit -m "feat: event router, webhook, main — full bot loop working"
```

---

## Phase 1 Complete ✓

At this point the bot can:
- Receive verified LINE webhook events
- Handle follow events — send welcome with persona selection quick replies
- Route persona selection taps to `booking_assistant` or `sales_agent`
- Call Claude with the correct persona system prompt
- Auto-detect language changes via `[LANG:xx]` sentinel and save to DB
- Apply rate limiting and daily cost kill switch
- Store conversation history per user/agent

**Next:** Phase 2 — Booking System (slot generation, LIFF booking flow, admin schedule tab).
