from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import CheckResult, Monitor, User


def _alert_kind(previous_up: bool | None, is_up: bool) -> str | None:
    """Legacy helper kept for unit tests / simple transitions."""
    if previous_up is None:
        return "down" if not is_up else None
    if previous_up and not is_up:
        return "down"
    if not previous_up and is_up:
        return "recovered"
    return None


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


async def _post_discord(webhook_url: str, *, title: str, description: str, color: int) -> None:
    payload = {
        "username": "PulseCheck",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "footer": {"text": "PulseCheck uptime monitor"},
            }
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            await client.post(webhook_url, json=payload)
    except httpx.HTTPError:
        return


async def _confirmed_down(db: AsyncSession, monitor_id: int, confirmations: int) -> bool:
    if confirmations <= 1:
        return True
    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc())
        .limit(confirmations)
    )
    rows = list(result.scalars().all())
    if len(rows) < confirmations:
        return False
    return all(not row.is_up for row in rows)


async def maybe_alert_owner(
    db: AsyncSession,
    owner: User | None,
    monitor: Monitor,
    result: CheckResult,
    previous_up: bool | None,
) -> None:
    """Send Discord alerts with confirmation, cooldown, recovery, and SSL warnings."""
    if owner is None or not owner.discord_webhook_url:
        return

    settings = get_settings()
    now = datetime.now(UTC)
    webhook = owner.discord_webhook_url
    dirty = False

    if result.is_up:
        if monitor.last_alert_kind == "down":
            latency = (
                f"{round(result.response_time_ms)} ms"
                if result.response_time_ms is not None
                else "n/a"
            )
            await _post_discord(
                webhook,
                title=f"RECOVERED · {monitor.name}",
                description=(
                    f"**{monitor.url}** is back up.\n"
                    f"Status: `{result.status_code}` · Latency: `{latency}`"
                ),
                color=0x34D399,
            )
            monitor.last_alert_kind = "up"
            monitor.last_alert_at = now
            dirty = True
    else:
        confirmed = await _confirmed_down(db, monitor.id, settings.alert_confirmations)
        if confirmed and monitor.last_alert_kind != "down":
            last_at = _aware(monitor.last_alert_at)
            cooldown_ok = True
            if last_at is not None and monitor.last_alert_kind == "down":
                cooldown_ok = (now - last_at).total_seconds() >= settings.alert_cooldown_seconds
            if cooldown_ok:
                await _post_discord(
                    webhook,
                    title=f"DOWN · {monitor.name}",
                    description=(
                        f"**{monitor.url}** failed {settings.alert_confirmations} consecutive checks.\n"
                        f"Status: `{result.status_code or 'n/a'}`\n"
                        f"Error: {result.error_message or 'none'}"
                    ),
                    color=0xF87171,
                )
                monitor.last_alert_kind = "down"
                monitor.last_alert_at = now
                dirty = True

    # SSL expiry warning (at most once per 7 days).
    if result.details_json:
        try:
            details = json.loads(result.details_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            details = None
        if isinstance(details, dict):
            days = details.get("ssl_days_remaining")
            ssl_warning = bool(details.get("ssl_warning")) or (
                isinstance(days, int) and days <= settings.ssl_warn_days
            )
            if ssl_warning and isinstance(days, int):
                last_ssl = _aware(monitor.last_ssl_alert_at)
                should_ssl = last_ssl is None or (now - last_ssl).total_seconds() >= 7 * 24 * 3600
                if should_ssl:
                    await _post_discord(
                        webhook,
                        title=f"SSL WARNING · {monitor.name}",
                        description=(
                            f"**{monitor.url}** certificate expires in **{days}** day(s).\n"
                            f"Issuer: `{details.get('ssl_issuer') or 'unknown'}`"
                        ),
                        color=0xFBBF24,
                    )
                    monitor.last_ssl_alert_at = now
                    dirty = True

    if dirty:
        await db.commit()
        await db.refresh(monitor)

    # Keep previous_up referenced so call sites remain compatible.
    _ = previous_up
