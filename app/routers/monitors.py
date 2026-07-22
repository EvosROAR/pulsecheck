import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models import CheckResult, Monitor, User
from app.schemas import (
    CheckAllResponse,
    CheckResultRead,
    IncidentRead,
    MonitorCreate,
    MonitorRead,
    MonitorStats,
    MonitorUpdate,
    PublicMonitorStatus,
)
from app.services.incidents import get_incidents
from app.services.monitors import (
    apply_public_enabled,
    get_monitor_stats,
    get_monitor_with_owner,
    get_public_status,
    get_stats_for_owner,
    run_check,
    run_checks_for_owner,
)

router = APIRouter(prefix="/monitors", tags=["monitors"])
public_router = APIRouter(prefix="/public", tags=["public"])


async def _get_owned_monitor(db: AsyncSession, monitor_id: int, user: User) -> Monitor:
    monitor = await get_monitor_with_owner(db, monitor_id, user.id)
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


@router.post("", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    payload: MonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Monitor:
    keyword = (payload.expected_body_contains or "").strip() or None
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        interval_seconds=payload.interval_seconds,
        expected_status=payload.expected_status,
        expected_body_contains=keyword,
        owner_id=current_user.id,
    )
    db.add(monitor)
    await db.commit()
    await db.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorRead])
async def list_monitors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Monitor]:
    result = await db.execute(
        select(Monitor).where(Monitor.owner_id == current_user.id).order_by(Monitor.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/check-all", response_model=CheckAllResponse)
async def check_all_monitors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckAllResponse:
    results = await run_checks_for_owner(db, current_user.id)
    return CheckAllResponse(checked=len(results), results=results)


@router.get("/stats/summary", response_model=list[MonitorStats])
async def stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MonitorStats]:
    return await get_stats_for_owner(db, current_user.id)


@router.get("/{monitor_id}", response_model=MonitorRead)
async def get_monitor(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Monitor:
    return await _get_owned_monitor(db, monitor_id, current_user)


@router.patch("/{monitor_id}", response_model=MonitorRead)
async def update_monitor(
    monitor_id: int,
    payload: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Monitor:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    public_enabled = data.pop("public_enabled", None)
    if "url" in data and data["url"] is not None:
        data["url"] = str(data["url"])
    if "expected_body_contains" in data:
        value = data["expected_body_contains"]
        data["expected_body_contains"] = (value or "").strip() or None
    for key, value in data.items():
        setattr(monitor, key, value)
    if public_enabled is not None:
        apply_public_enabled(monitor, public_enabled)
    await db.commit()
    await db.refresh(monitor)
    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitor(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    await db.delete(monitor)
    await db.commit()


@router.post("/{monitor_id}/check", response_model=CheckResultRead)
async def trigger_check(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CheckResult:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    return await run_check(db, monitor)


@router.get("/{monitor_id}/checks", response_model=list[CheckResultRead])
async def list_checks(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CheckResult]:
    await _get_owned_monitor(db, monitor_id, current_user)
    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{monitor_id}/export.csv")
async def export_checks_csv(
    monitor_id: int,
    limit: int = Query(default=500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(limit)
    )
    rows = list(result.scalars().all())
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["checked_at", "is_up", "status_code", "response_time_ms", "error_message", "status_label"]
    )
    for row in rows:
        info = CheckResultRead.model_validate(row)
        checked_at = info.checked_at
        if hasattr(checked_at, "isoformat"):
            checked_at = checked_at.isoformat().replace("+00:00", "Z")
        writer.writerow(
            [
                checked_at,
                info.is_up,
                info.status_code,
                info.response_time_ms,
                info.error_message or "",
                info.status_label,
            ]
        )
    buffer.seek(0)
    filename = f"pulsecheck-{monitor.id}-checks.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{monitor_id}/stats", response_model=MonitorStats)
async def monitor_stats(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitorStats:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    return await get_monitor_stats(db, monitor)


@router.get("/{monitor_id}/incidents", response_model=list[IncidentRead])
async def monitor_incidents(
    monitor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IncidentRead]:
    await _get_owned_monitor(db, monitor_id, current_user)
    return await get_incidents(db, monitor_id, limit=limit)


@public_router.get("/status/{slug}", response_model=PublicMonitorStatus)
async def public_status(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublicMonitorStatus:
    payload = await get_public_status(db, slug)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Status page not found")
    return payload
