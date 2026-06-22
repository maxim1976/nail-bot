from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


def start_scheduler() -> None:
    global _scheduler
    from app.cron import send_24h_reminders

    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="Asia/Taipei")
        _scheduler.add_job(
            send_24h_reminders,
            IntervalTrigger(minutes=10),
            id="reminders",
            replace_existing=True,
        )
    if not _scheduler.running:
        _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
