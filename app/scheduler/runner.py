from __future__ import annotations

from typing import Optional, Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover
    BackgroundScheduler = None  # type: ignore

from app.scheduler.jobs import daily_analytics_capsule
from app.scheduler.task_worker import run_due
from app.settings import settings


def start_scheduler() -> Optional[Any]:
    """Start the local scheduler if APScheduler is installed.

    The project is designed to run fully offline; scheduled jobs are optional.
    If APScheduler isn't installed, this is a no-op.
    """
    if BackgroundScheduler is None:
        return None

    sched = BackgroundScheduler()
    sched.add_job(daily_analytics_capsule, "interval", hours=24, id="daily_analytics")

    # Optional: auto-run queued tasks (local-only). Enable with EV_WORKER_AUTORUN=1
    if settings.worker_autorun:
        sched.add_job(lambda: run_due(max_tasks=1), "interval", seconds=int(settings.worker_interval_seconds), id="task_worker")

    sched.start()
    return sched
