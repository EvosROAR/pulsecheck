from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class ProbeResult:
    is_up: bool
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None


async def probe_url(url: str, expected_status: int = 200) -> ProbeResult:
    """Hit a URL once and return uptime + latency details."""
    settings = get_settings()
    started = time.perf_counter()

    try:
        async with httpx.AsyncClient(
            timeout=settings.check_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            elapsed_ms = (time.perf_counter() - started) * 1000
            is_up = response.status_code == expected_status
            return ProbeResult(
                is_up=is_up,
                status_code=response.status_code,
                response_time_ms=round(elapsed_ms, 2),
                error_message=None
                if is_up
                else f"Expected status {expected_status}, got {response.status_code}",
            )
    except httpx.TimeoutException:
        return ProbeResult(
            is_up=False,
            status_code=None,
            response_time_ms=None,
            error_message="Request timed out",
        )
    except httpx.HTTPError as exc:
        return ProbeResult(
            is_up=False,
            status_code=None,
            response_time_ms=None,
            error_message=str(exc),
        )
