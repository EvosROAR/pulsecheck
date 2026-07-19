from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import CheckResult, Monitor
from app.services.monitors import run_check

logger = logging.getLogger("pulsecheck.scheduler")


async def _due_monitors(session) -> list[Monitor]:
    result = await session.execute(
        select(Monitor)
        .where(Monitor.is_active.is_(True))
        .options(selectinload(Monitor.owner))
    )
    monitors = list(result.scalars().all())
    due: list[Monitor] = []
    now = datetime.now(UTC)

    for monitor in monitors:
        latest = await session.execute(
            select(CheckResult)
            .where(CheckResult.monitor_id == monitor.id)
            .order_by(CheckResult.checked_at.desc())
            .limit(1)
        )
        last = latest.scalar_one_or_none()
        if last is None:
            due.append(monitor)
            continue

        checked_at = last.checked_at
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=UTC)
        elapsed = (now - checked_at).total_seconds()
        if elapsed >= monitor.interval_seconds:
            due.append(monitor)
    return due


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    logger.info("Auto-check scheduler started (tick=%ss)", settings.scheduler_tick_seconds)

    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as session:
                due = await _due_monitors(session)
                for monitor in due:
                    try:
                        await run_check(session, monitor, notify=True)
                        logger.info("Auto-checked monitor id=%s name=%s", monitor.id, monitor.name)
                    except Exception:
                        logger.exception("Failed auto-check for monitor id=%s", monitor.id)
        except Exception:
            logger.exception("Scheduler tick failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.scheduler_tick_seconds)
        except TimeoutError:
            continue

    logger.info("Auto-check scheduler stopped")
