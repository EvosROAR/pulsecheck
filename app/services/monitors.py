from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckResult, Monitor
from app.schemas import MonitorStats
from app.services.checker import probe_url


async def run_check(db: AsyncSession, monitor: Monitor) -> CheckResult:
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
        last_checked_at=last.checked_at if last else None,
    )
