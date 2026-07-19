from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CheckResult, Monitor, User
from app.schemas import MonitorStats
from app.services.alerts import maybe_alert_owner
from app.services.checker import probe_url
from app.status_labels import categorize_http_status


async def run_check(
    db: AsyncSession,
    monitor: Monitor,
    *,
    notify: bool = True,
) -> CheckResult:
    previous = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor.id)
        .order_by(CheckResult.checked_at.desc())
        .limit(1)
    )
    previous_result = previous.scalar_one_or_none()
    previous_up = previous_result.is_up if previous_result else None

    probe = await probe_url(monitor.url, monitor.expected_status)
    result = CheckResult(
        monitor_id=monitor.id,
        is_up=probe.is_up,
        status_code=probe.status_code,
        response_time_ms=probe.response_time_ms,
        error_message=probe.error_message,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    if notify:
        owner = getattr(monitor, "owner", None)
        if owner is None:
            owner_result = await db.execute(select(User).where(User.id == monitor.owner_id))
            owner = owner_result.scalar_one_or_none()
        await maybe_alert_owner(owner, monitor, result, previous_up)

    return result


async def get_monitor_stats(db: AsyncSession, monitor: Monitor) -> MonitorStats:
    totals = await db.execute(
        select(
            func.count(CheckResult.id),
            func.sum(case((CheckResult.is_up.is_(True), 1), else_=0)),
            func.avg(CheckResult.response_time_ms),
        ).where(CheckResult.monitor_id == monitor.id)
    )
    total_checks, up_sum, avg_rt = totals.one()
    total_checks = int(total_checks or 0)
    up_checks = int(up_sum or 0)
    down_checks = total_checks - up_checks
    uptime = round((up_checks / total_checks) * 100, 2) if total_checks else 0.0

    latest = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor.id)
        .order_by(CheckResult.checked_at.desc())
        .limit(1)
    )
    last = latest.scalar_one_or_none()
    last_info = (
        categorize_http_status(last.status_code, last.error_message) if last is not None else None
    )

    return MonitorStats(
        monitor_id=monitor.id,
        name=monitor.name,
        url=monitor.url,
        total_checks=total_checks,
        up_checks=up_checks,
        down_checks=down_checks,
        uptime_percentage=uptime,
        avg_response_time_ms=round(float(avg_rt), 2) if avg_rt is not None else None,
        last_status="up" if last and last.is_up else ("down" if last else None),
        last_status_category=last_info.category if last_info else None,
        last_status_label=last_info.label if last_info else None,
        last_status_tone=last_info.tone if last_info else None,
        last_checked_at=last.checked_at if last else None,
    )


async def get_monitor_with_owner(db: AsyncSession, monitor_id: int, owner_id: int) -> Monitor | None:
    result = await db.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id, Monitor.owner_id == owner_id)
        .options(selectinload(Monitor.owner))
    )
    return result.scalar_one_or_none()
