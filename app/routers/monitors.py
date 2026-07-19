from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models import CheckResult, Monitor, User
from app.schemas import CheckResultRead, MonitorCreate, MonitorRead, MonitorStats, MonitorUpdate
from app.services.monitors import get_monitor_stats, run_check

router = APIRouter(prefix="/monitors", tags=["monitors"])


async def _get_owned_monitor(db: AsyncSession, monitor_id: int, user: User) -> Monitor:
    result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.owner_id == user.id)
    )
    monitor = result.scalar_one_or_none()
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


@router.post("", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    payload: MonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Monitor:
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        interval_seconds=payload.interval_seconds,
        expected_status=payload.expected_status,
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
    if "url" in data and data["url"] is not None:
        data["url"] = str(data["url"])
    for key, value in data.items():
        setattr(monitor, key, value)
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


@router.get("/{monitor_id}/stats", response_model=MonitorStats)
async def monitor_stats(
    monitor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonitorStats:
    monitor = await _get_owned_monitor(db, monitor_id, current_user)
    return await get_monitor_stats(db, monitor)
