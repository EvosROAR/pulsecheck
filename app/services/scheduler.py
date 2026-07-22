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
from app.services.retention import purge_old_checks

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


async def _run_one(monitor_id: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Monitor)
            .where(Monitor.id == monitor_id)
            .options(selectinload(Monitor.owner))
        )
        monitor = result.scalar_one_or_none()
        if monitor is None or not monitor.is_active:
            return
        await run_check(session, monitor, notify=True)
        logger.info("Auto-checked monitor id=%s name=%s", monitor.id, monitor.name)


async def scheduler_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    logger.info(
        "Auto-check scheduler started (tick=%ss, concurrency=%s)",
        settings.scheduler_tick_seconds,
        settings.scheduler_concurrency,
    )
    ticks = 0

    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as session:
                due = await _due_monitors(session)
                due_ids = [m.id for m in due]

            if due_ids:
                sem = asyncio.Semaphore(max(1, settings.scheduler_concurrency))

                async def _guarded(mid: int) -> None:
                    async with sem:
                        try:
                            await _run_one(mid)
                        except Exception:
                            logger.exception("Failed auto-check for monitor id=%s", mid)

                await asyncio.gather(*[_guarded(mid) for mid in due_ids])

            ticks += 1
            # Purge old history about once per hour (depending on tick).
            if ticks % max(1, int(3600 / max(1, settings.scheduler_tick_seconds))) == 0:
                try:
                    await purge_old_checks()
                except Exception:
                    logger.exception("Retention purge failed")
        except Exception:
            logger.exception("Scheduler tick failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.scheduler_tick_seconds)
        except TimeoutError:
            continue

    logger.info("Auto-check scheduler stopped")
