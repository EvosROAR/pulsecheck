import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CheckResult, Monitor, User
from app.schemas import MonitorStats, ProbeInsightsRead, PublicMonitorStatus, CheckResultRead
from app.services.alerts import maybe_alert_owner
from app.services.checker import probe_url
from app.services.probe_insights import build_probe_insights
from app.status_labels import categorize_http_status


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return round(ordered[low] * (1 - weight) + ordered[high] * weight, 2)


async def _uptime_since(db: AsyncSession, monitor_id: int, since: datetime) -> float | None:
    totals = await db.execute(
        select(
            func.count(CheckResult.id),
            func.sum(case((CheckResult.is_up.is_(True), 1), else_=0)),
        ).where(CheckResult.monitor_id == monitor_id, CheckResult.checked_at >= since)
    )
    total_checks, up_sum = totals.one()
    total_checks = int(total_checks or 0)
    if total_checks == 0:
        return None
    return round((int(up_sum or 0) / total_checks) * 100, 2)


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

    probe = await probe_url(
        monitor.url,
        monitor.expected_status,
        expected_body_contains=monitor.expected_body_contains,
    )
    insights = await build_probe_insights(
        url=monitor.url,
        expected_status=monitor.expected_status,
        is_up=probe.is_up,
        status_code=probe.status_code,
        response_time_ms=probe.response_time_ms,
        error_message=probe.error_message,
        headers=probe.headers,
        response_size_bytes=probe.response_size_bytes,
        status_info=probe.status_info,
        final_url=probe.final_url,
        keyword_matched=probe.keyword_matched,
    )
    result = CheckResult(
        monitor_id=monitor.id,
        is_up=probe.is_up,
        status_code=probe.status_code,
        response_time_ms=probe.response_time_ms,
        error_message=probe.error_message,
        details_json=insights.to_json(),
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

    now = datetime.now(UTC)
    uptime_24h = await _uptime_since(db, monitor.id, now - timedelta(hours=24))
    uptime_7d = await _uptime_since(db, monitor.id, now - timedelta(days=7))

    latency_rows = await db.execute(
        select(CheckResult.response_time_ms)
        .where(
            CheckResult.monitor_id == monitor.id,
            CheckResult.response_time_ms.is_not(None),
        )
        .order_by(CheckResult.checked_at.desc())
        .limit(100)
    )
    latencies = [float(value) for (value,) in latency_rows.all() if value is not None]
    p95 = _percentile(latencies, 0.95)

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
    last_insights = None
    if last is not None and last.details_json:
        try:
            last_insights = ProbeInsightsRead.model_validate(json.loads(last.details_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            last_insights = None

    return MonitorStats(
        monitor_id=monitor.id,
        name=monitor.name,
        url=monitor.url,
        total_checks=total_checks,
        up_checks=up_checks,
        down_checks=down_checks,
        uptime_percentage=uptime,
        uptime_24h=uptime_24h,
        uptime_7d=uptime_7d,
        avg_response_time_ms=round(float(avg_rt), 2) if avg_rt is not None else None,
        p95_response_time_ms=p95,
        last_status="up" if last and last.is_up else ("down" if last else None),
        last_status_category=last_info.category if last_info else None,
        last_status_label=last_info.label if last_info else None,
        last_status_tone=last_info.tone if last_info else None,
        last_insights=last_insights,
        last_checked_at=last.checked_at if last else None,
        is_active=monitor.is_active,
        public_slug=monitor.public_slug,
        expected_body_contains=monitor.expected_body_contains,
    )


async def get_public_status(db: AsyncSession, slug: str) -> PublicMonitorStatus | None:
    result = await db.execute(select(Monitor).where(Monitor.public_slug == slug))
    monitor = result.scalar_one_or_none()
    if monitor is None:
        return None
    stats = await get_monitor_stats(db, monitor)
    checks = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor.id)
        .order_by(CheckResult.checked_at.desc())
        .limit(20)
    )
    return PublicMonitorStatus(
        name=monitor.name,
        url=monitor.url,
        is_active=monitor.is_active,
        uptime_percentage=stats.uptime_percentage,
        uptime_24h=stats.uptime_24h,
        avg_response_time_ms=stats.avg_response_time_ms,
        last_status=stats.last_status,
        last_status_label=stats.last_status_label,
        last_status_tone=stats.last_status_tone,
        last_checked_at=stats.last_checked_at,
        recent_checks=[CheckResultRead.model_validate(row) for row in checks.scalars().all()],
    )


def apply_public_enabled(monitor: Monitor, enabled: bool) -> None:
    if enabled:
        if not monitor.public_slug:
            monitor.public_slug = secrets.token_urlsafe(9)
    else:
        monitor.public_slug = None


async def get_monitor_with_owner(db: AsyncSession, monitor_id: int, owner_id: int) -> Monitor | None:
    result = await db.execute(
        select(Monitor)
        .where(Monitor.id == monitor_id, Monitor.owner_id == owner_id)
        .options(selectinload(Monitor.owner))
    )
    return result.scalar_one_or_none()


async def run_checks_for_owner(db: AsyncSession, owner_id: int) -> list[CheckResult]:
    result = await db.execute(
        select(Monitor)
        .where(Monitor.owner_id == owner_id, Monitor.is_active.is_(True))
        .options(selectinload(Monitor.owner))
        .order_by(Monitor.id.asc())
    )
    monitors = list(result.scalars().all())
    checks: list[CheckResult] = []
    for monitor in monitors:
        checks.append(await run_check(db, monitor))
    return checks
