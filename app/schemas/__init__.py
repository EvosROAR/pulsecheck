from datetime import UTC, datetime
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_serializer, model_validator

from app.status_labels import categorize_http_status


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    discord_webhook_url: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _to_utc_iso(value)  # type: ignore[return-value]


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    discord_webhook_url: str | None = Field(default=None, max_length=500)


class MonitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: HttpUrl
    interval_seconds: int = Field(default=60, ge=30, le=3600)
    expected_status: int = Field(default=200, ge=100, le=599)
    expected_body_contains: str | None = Field(default=None, max_length=200)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    url: HttpUrl | None = None
    interval_seconds: int | None = Field(default=None, ge=30, le=3600)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    expected_body_contains: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None
    public_enabled: bool | None = None


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    expected_body_contains: str | None = None
    is_active: bool
    public_slug: str | None = None
    created_at: datetime
    owner_id: int

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _to_utc_iso(value)  # type: ignore[return-value]


class ProbeInsightsRead(BaseModel):
    status_category: str | None = None
    status_label: str | None = None
    status_tone: str | None = None
    response_time_ms: float | None = None
    response_size_bytes: int | None = None
    probe_region: str | None = None
    ip_addresses: list[str] = []
    dns_ok: bool | None = None
    dns_error: str | None = None
    ssl_checked: bool | None = None
    ssl_valid: bool | None = None
    ssl_issuer: str | None = None
    ssl_expires_at: str | None = None
    ssl_days_remaining: int | None = None
    ssl_warning: bool | None = None
    ssl_error: str | None = None
    server: str | None = None
    cdn: str | None = None
    tech_stack: list[str] = []
    security_headers: dict[str, bool] = {}
    security_score: int | None = None
    final_url: str | None = None
    redirected: bool | None = None
    keyword_matched: bool | None = None
    error_analysis: str | None = None


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    is_up: bool
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    details_json: str | None = None
    checked_at: datetime
    status_category: str = "unknown"
    status_label: str = "UNKNOWN"
    status_tone: str = "unknown"
    details: ProbeInsightsRead | None = None

    @model_validator(mode="after")
    def attach_status_category(self) -> "CheckResultRead":
        info = categorize_http_status(self.status_code, self.error_message)
        self.status_category = info.category
        self.status_label = info.label
        self.status_tone = info.tone
        if self.details_json and self.details is None:
            try:
                payload: dict[str, Any] = json.loads(self.details_json)
                self.details = ProbeInsightsRead.model_validate(payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                self.details = None
        return self

    @field_serializer("checked_at")
    def serialize_checked_at(self, value: datetime) -> str:
        return _to_utc_iso(value)  # type: ignore[return-value]


class MonitorStats(BaseModel):
    monitor_id: int
    name: str
    url: str
    total_checks: int
    up_checks: int
    down_checks: int
    uptime_percentage: float
    uptime_24h: float | None = None
    uptime_7d: float | None = None
    avg_response_time_ms: float | None
    p95_response_time_ms: float | None = None
    last_status: str | None
    last_status_category: str | None = None
    last_status_label: str | None = None
    last_status_tone: str | None = None
    last_insights: ProbeInsightsRead | None = None
    last_checked_at: datetime | None
    is_active: bool = True
    public_slug: str | None = None
    expected_body_contains: str | None = None

    @field_serializer("last_checked_at")
    def serialize_last_checked_at(self, value: datetime | None) -> str | None:
        return _to_utc_iso(value)


class PublicMonitorStatus(BaseModel):
    name: str
    url: str
    is_active: bool
    uptime_percentage: float
    uptime_24h: float | None = None
    avg_response_time_ms: float | None
    last_status: str | None
    last_status_label: str | None = None
    last_status_tone: str | None = None
    last_checked_at: datetime | None
    recent_checks: list[CheckResultRead] = []

    @field_serializer("last_checked_at")
    def serialize_last_checked_at(self, value: datetime | None) -> str | None:
        return _to_utc_iso(value)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


class MetaResponse(BaseModel):
    app: str
    version: str
    probe_region: str
    probe_note: str


class CheckAllResponse(BaseModel):
    checked: int
    results: list[CheckResultRead]
