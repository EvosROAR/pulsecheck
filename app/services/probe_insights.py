from __future__ import annotations

import asyncio
import json
import socket
import ssl
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.status_labels import StatusInfo, categorize_http_status


SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
)


@dataclass(slots=True)
class ProbeInsights:
    status_category: str
    status_label: str
    status_tone: str
    response_time_ms: float | None
    response_size_bytes: int | None
    probe_region: str
    ip_addresses: list[str] = field(default_factory=list)
    dns_ok: bool = False
    dns_error: str | None = None
    ssl_checked: bool = False
    ssl_valid: bool | None = None
    ssl_issuer: str | None = None
    ssl_expires_at: str | None = None
    ssl_days_remaining: int | None = None
    ssl_warning: bool = False
    ssl_error: str | None = None
    server: str | None = None
    cdn: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    security_headers: dict[str, bool] = field(default_factory=dict)
    security_score: int = 0
    final_url: str | None = None
    redirected: bool | None = None
    keyword_matched: bool | None = None
    error_analysis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def _detect_cdn(headers: dict[str, str]) -> str | None:
    lowered = {k.lower(): v for k, v in headers.items()}
    server = (lowered.get("server") or "").lower()
    if "cf-ray" in lowered or "cloudflare" in server:
        return "Cloudflare"
    if "x-amz-cf-id" in lowered or "x-amz-cf-pop" in lowered:
        return "Amazon CloudFront"
    if "x-vercel-id" in lowered or "x-vercel-cache" in lowered:
        return "Vercel"
    if "x-nf-request-id" in lowered or "netlify" in server:
        return "Netlify"
    if "x-served-by" in lowered and "fastly" in (lowered.get("x-served-by") or "").lower():
        return "Fastly"
    if "akamai" in server or "x-akamai-transformed" in lowered:
        return "Akamai"
    if "x-cache" in lowered and "cloudfront" in (lowered.get("via") or "").lower():
        return "Amazon CloudFront"
    return None


def _detect_tech_stack(headers: dict[str, str]) -> list[str]:
    lowered = {k.lower(): v for k, v in headers.items()}
    found: list[str] = []
    powered = lowered.get("x-powered-by")
    if powered:
        found.append(powered)
    server = lowered.get("server")
    if server:
        # Keep raw server token as stack hint when not only a CDN brand.
        token = server.split("/")[0]
        if token and token.lower() not in {"cloudflare", "netlify"}:
            found.append(server)
    generator = lowered.get("x-generator")
    if generator:
        found.append(generator)
    if lowered.get("x-aspnet-version") or lowered.get("x-aspnetmvc-version"):
        found.append("ASP.NET")
    # de-dupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for item in found:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:6]


def _security_headers(headers: dict[str, str]) -> tuple[dict[str, bool], int]:
    lowered = {k.lower(): v for k, v in headers.items()}
    present = {name: name in lowered and bool(lowered[name]) for name in SECURITY_HEADERS}
    score = int(round((sum(1 for ok in present.values() if ok) / len(SECURITY_HEADERS)) * 100))
    return present, score


def _resolve_dns(hostname: str) -> tuple[list[str], str | None]:
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips = sorted({item[4][0] for item in infos})
        return ips, None
    except OSError as exc:
        return [], str(exc)


def _inspect_ssl(hostname: str, port: int = 443) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ssl_checked": True,
        "ssl_valid": None,
        "ssl_issuer": None,
        "ssl_expires_at": None,
        "ssl_days_remaining": None,
        "ssl_error": None,
    }
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=8) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        issuer_parts = cert.get("issuer") or ()
        issuer = ", ".join(value for group in issuer_parts for (_, value) in group)
        not_after = cert.get("notAfter")
        expires_at = None
        days_remaining = None
        if not_after:
            expires = parsedate_to_datetime(not_after)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            expires_at = expires.astimezone(UTC).isoformat().replace("+00:00", "Z")
            days_remaining = (expires - datetime.now(UTC)).days
        result.update(
            {
                "ssl_valid": True,
                "ssl_issuer": issuer or None,
                "ssl_expires_at": expires_at,
                "ssl_days_remaining": days_remaining,
            }
        )
    except Exception as exc:  # noqa: BLE001 - surface any TLS failure as insight
        result["ssl_valid"] = False
        result["ssl_error"] = str(exc)
    return result


def _error_analysis(
    *,
    is_up: bool,
    status_info: StatusInfo,
    expected_status: int,
    status_code: int | None,
    error_message: str | None,
    ssl_valid: bool | None,
) -> str | None:
    if is_up:
        return "Target responded with the expected status."
    parts: list[str] = [f"Classified as {status_info.label}."]
    if status_code is not None:
        parts.append(f"Got HTTP {status_code}, expected {expected_status}.")
    if error_message:
        parts.append(error_message)
    if ssl_valid is False:
        parts.append("TLS/SSL handshake or certificate validation failed.")
    return " ".join(parts)


async def build_probe_insights(
    *,
    url: str,
    expected_status: int,
    is_up: bool,
    status_code: int | None,
    response_time_ms: float | None,
    error_message: str | None,
    headers: dict[str, str] | None = None,
    response_size_bytes: int | None = None,
    status_info: StatusInfo | None = None,
    final_url: str | None = None,
    keyword_matched: bool | None = None,
) -> ProbeInsights:
    settings = get_settings()
    info = status_info or categorize_http_status(status_code, error_message)
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    headers = headers or {}

    ip_addresses: list[str] = []
    dns_error: str | None = None
    dns_ok = False
    ssl_data: dict[str, Any] = {
        "ssl_checked": False,
        "ssl_valid": None,
        "ssl_issuer": None,
        "ssl_expires_at": None,
        "ssl_days_remaining": None,
        "ssl_error": None,
    }

    if hostname:
        ip_addresses, dns_error = await asyncio.to_thread(_resolve_dns, hostname)
        dns_ok = bool(ip_addresses) and dns_error is None
        if parsed.scheme == "https":
            port = parsed.port or 443
            ssl_data = await asyncio.to_thread(_inspect_ssl, hostname, port)

    security_headers, security_score = _security_headers(headers)
    lowered = {k.lower(): v for k, v in headers.items()}
    days_remaining = ssl_data.get("ssl_days_remaining")
    ssl_warning = bool(
        ssl_data.get("ssl_valid") is True
        and isinstance(days_remaining, int)
        and days_remaining <= 14
    )
    resolved_final = final_url or url
    redirected = None
    if final_url:
        redirected = final_url.rstrip("/") != url.rstrip("/")

    return ProbeInsights(
        status_category=info.category,
        status_label=info.label,
        status_tone=info.tone,
        response_time_ms=response_time_ms,
        response_size_bytes=response_size_bytes,
        probe_region=settings.probe_region,
        ip_addresses=ip_addresses,
        dns_ok=dns_ok,
        dns_error=dns_error,
        ssl_checked=bool(ssl_data.get("ssl_checked")),
        ssl_valid=ssl_data.get("ssl_valid"),
        ssl_issuer=ssl_data.get("ssl_issuer"),
        ssl_expires_at=ssl_data.get("ssl_expires_at"),
        ssl_days_remaining=days_remaining,
        ssl_warning=ssl_warning,
        ssl_error=ssl_data.get("ssl_error"),
        server=lowered.get("server"),
        cdn=_detect_cdn(headers),
        tech_stack=_detect_tech_stack(headers),
        security_headers=security_headers,
        security_score=security_score,
        final_url=resolved_final,
        redirected=redirected,
        keyword_matched=keyword_matched,
        error_analysis=_error_analysis(
            is_up=is_up,
            status_info=info,
            expected_status=expected_status,
            status_code=status_code,
            error_message=error_message,
            ssl_valid=ssl_data.get("ssl_valid"),
        ),
    )
