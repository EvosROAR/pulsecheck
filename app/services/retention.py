from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models import CheckResult

logger = logging.getLogger("pulsecheck.retention")


async def purge_old_checks() -> int:
    """Delete check rows older than configured retention window."""
    settings = get_settings()
    days = settings.check_retention_days
    if days <= 0:
        return 0

    cutoff = datetime.now(UTC) - timedelta(days=days)
    async with AsyncSessionLocal() as session:
        count_result = await session.execute(
            select(func.count(CheckResult.id)).where(CheckResult.checked_at < cutoff)
        )
        to_delete = int(count_result.scalar_one() or 0)
        if to_delete == 0:
            return 0
        await session.execute(delete(CheckResult).where(CheckResult.checked_at < cutoff))
        await session.commit()
        logger.info("Purged %s old check rows (older than %s days)", to_delete, days)
        return to_delete
