from __future__ import annotations

import httpx

from app.models import CheckResult, Monitor, User


def _alert_kind(previous_up: bool | None, is_up: bool) -> str | None:
    if previous_up is None:
        return "down" if not is_up else None
    if previous_up and not is_up:
        return "down"
    if not previous_up and is_up:
        return "recovered"
    return None


async def send_discord_alert(
    webhook_url: str,
    *,
    monitor: Monitor,
    result: CheckResult,
    previous_up: bool | None,
) -> None:
    """Notify Discord when a monitor goes down or recovers."""
    if not webhook_url:
        return

    kind = _alert_kind(previous_up, result.is_up)
    if kind is None:
        return

    if kind == "down":
        title = f"DOWN · {monitor.name}"
        color = 0xF87171
        description = (
            f"**{monitor.url}** is not responding as expected.\n"
            f"Status: `{result.status_code or 'n/a'}`\n"
            f"Error: {result.error_message or 'none'}"
        )
    else:
        title = f"RECOVERED · {monitor.name}"
        color = 0x34D399
        latency = (
            f"{round(result.response_time_ms)} ms" if result.response_time_ms is not None else "n/a"
        )
        description = (
            f"**{monitor.url}** is back up.\n"
            f"Status: `{result.status_code}` · Latency: `{latency}`"
        )

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
        # Alerts must never break the monitoring loop.
        return


async def maybe_alert_owner(
    owner: User | None,
    monitor: Monitor,
    result: CheckResult,
    previous_up: bool | None,
) -> None:
    if owner is None or not owner.discord_webhook_url:
        return
    await send_discord_alert(
        owner.discord_webhook_url,
        monitor=monitor,
        result=result,
        previous_up=previous_up,
    )
