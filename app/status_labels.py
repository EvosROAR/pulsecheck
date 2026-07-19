from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatusInfo:
    category: str
    label: str
    tone: str  # up | warn | down | info | unknown


def categorize_http_status(status_code: int | None, error_message: str | None = None) -> StatusInfo:
    """Map HTTP / network outcomes to monitoring-friendly categories."""
    if status_code is None:
        return _categorize_network_error(error_message)

    if 100 <= status_code <= 199:
        return StatusInfo("informational", "INFORMATIONAL", "info")
    if 200 <= status_code <= 299:
        return StatusInfo("up", "UP", "up")
    if 300 <= status_code <= 399:
        return StatusInfo("redirect", "REDIRECT", "warn")
    if status_code == 401:
        return StatusInfo("unauthorized", "UNAUTHORIZED", "warn")
    if status_code == 403:
        return StatusInfo("forbidden", "FORBIDDEN", "warn")
    if status_code == 404:
        return StatusInfo("not_found", "NOT FOUND", "warn")
    if status_code == 408:
        return StatusInfo("timeout", "TIMEOUT", "down")
    if status_code == 429:
        return StatusInfo("rate_limited", "RATE LIMITED", "warn")
    if 400 <= status_code <= 499:
        return StatusInfo("client_error", "CLIENT ERROR", "warn")
    if 500 <= status_code <= 599:
        return StatusInfo("server_error", "SERVER ERROR", "down")
    return StatusInfo("unknown", f"HTTP {status_code}", "unknown")


def _categorize_network_error(error_message: str | None) -> StatusInfo:
    text = (error_message or "").lower()
    if "timed out" in text or "timeout" in text:
        return StatusInfo("timeout", "TIMEOUT", "down")
    if "name or service not known" in text or "getaddrinfo" in text or "nodename" in text:
        return StatusInfo("dns_error", "DNS ERROR", "down")
    if "certificate" in text or "ssl" in text or "tls" in text:
        return StatusInfo("ssl_error", "SSL ERROR", "down")
    if "connection refused" in text or "connect" in text:
        return StatusInfo("network_error", "NETWORK ERROR", "down")
    if error_message:
        return StatusInfo("network_error", "NETWORK ERROR", "down")
    return StatusInfo("unknown", "UNKNOWN", "unknown")
