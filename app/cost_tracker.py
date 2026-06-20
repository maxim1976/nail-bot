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
