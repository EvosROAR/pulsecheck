from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckResult
from app.schemas import IncidentRead
from app.status_labels import categorize_http_status


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def get_incidents(
    db: AsyncSession,
    monitor_id: int,
    *,
    limit: int = 20,
) -> list[IncidentRead]:
    """Build downtime incidents from consecutive failed checks."""
    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.asc())
        .limit(500)
    )
    rows = list(result.scalars().all())
    if not rows:
        return []

    incidents: list[IncidentRead] = []
    open_started: datetime | None = None
    open_ended: datetime | None = None
    open_count = 0
    open_code: int | None = None
    open_error: str | None = None

    def flush(*, ongoing: bool) -> None:
        nonlocal open_started, open_ended, open_count, open_code, open_error
        if open_started is None or open_ended is None or open_count == 0:
            return
        started = _aware(open_started)
        ended = _aware(open_ended)
        duration = None if ongoing else max(0, int((ended - started).total_seconds()))
        info = categorize_http_status(open_code, open_error)
        incidents.append(
            IncidentRead(
                started_at=started,
                ended_at=None if ongoing else ended,
                duration_seconds=duration,
                failed_checks=open_count,
                status_code=open_code,
                status_label=info.label,
                status_tone=info.tone,
                error_message=open_error,
                is_ongoing=ongoing,
            )
        )
        open_started = None
        open_ended = None
        open_count = 0
        open_code = None
        open_error = None

    for row in rows:
        if not row.is_up:
            if open_started is None:
                open_started = row.checked_at
                open_code = row.status_code
                open_error = row.error_message
            open_ended = row.checked_at
            open_count += 1
        else:
            flush(ongoing=False)

    if open_started is not None:
        flush(ongoing=True)

    incidents.reverse()
    return incidents[:limit]
