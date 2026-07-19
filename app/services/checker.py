from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings
from app.status_labels import StatusInfo, categorize_http_status


@dataclass(slots=True)
class ProbeResult:
    is_up: bool
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    status_info: StatusInfo
    headers: dict[str, str] = field(default_factory=dict)
    response_size_bytes: int | None = None
    final_url: str | None = None
    keyword_matched: bool | None = None


async def probe_url(
    url: str,
    expected_status: int = 200,
    *,
    expected_body_contains: str | None = None,
) -> ProbeResult:
    """Hit a URL once and return uptime + latency details."""
    settings = get_settings()
    started = time.perf_counter()
    keyword = (expected_body_contains or "").strip() or None

    try:
        async with httpx.AsyncClient(
            timeout=settings.check_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            elapsed_ms = (time.perf_counter() - started) * 1000
            body_text = response.text
            keyword_matched: bool | None = None
            if keyword:
                keyword_matched = keyword.lower() in body_text.lower()

            status_ok = response.status_code == expected_status
            is_up = status_ok and (keyword_matched is not False)
            info = categorize_http_status(response.status_code)
            headers = {k: v for k, v in response.headers.items()}

            error_message = None
            if not is_up:
                parts: list[str] = []
                if not status_ok:
                    parts.append(f"Expected status {expected_status}, got {response.status_code}")
                if keyword_matched is False:
                    parts.append(f"Expected body keyword not found: {keyword!r}")
                error_message = "; ".join(parts) or "Check failed"

            return ProbeResult(
                is_up=is_up,
                status_code=response.status_code,
                response_time_ms=round(elapsed_ms, 2),
                error_message=error_message,
                status_info=info,
                headers=headers,
                response_size_bytes=len(response.content),
                final_url=str(response.url),
                keyword_matched=keyword_matched,
            )
    except httpx.TimeoutException:
        info = categorize_http_status(None, "Request timed out")
        return ProbeResult(
            is_up=False,
            status_code=None,
            response_time_ms=None,
            error_message="Request timed out",
            status_info=info,
        )
    except httpx.HTTPError as exc:
        message = str(exc)
        info = categorize_http_status(None, message)
        return ProbeResult(
            is_up=False,
            status_code=None,
            response_time_ms=None,
            error_message=message,
            status_info=info,
        )
