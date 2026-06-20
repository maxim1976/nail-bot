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
