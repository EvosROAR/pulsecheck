from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


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
    created_at: datetime


class MonitorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: HttpUrl
    interval_seconds: int = Field(default=60, ge=30, le=3600)
    expected_status: int = Field(default=200, ge=100, le=599)


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    url: HttpUrl | None = None
    interval_seconds: int | None = Field(default=None, ge=30, le=3600)
    expected_status: int | None = Field(default=None, ge=100, le=599)
    is_active: bool | None = None


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    is_active: bool
    created_at: datetime
    owner_id: int


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    is_up: bool
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    checked_at: datetime


class MonitorStats(BaseModel):
    monitor_id: int
    name: str
    url: str
    total_checks: int
    up_checks: int
    down_checks: int
    uptime_percentage: float
    avg_response_time_ms: float | None
    last_status: str | None
    last_checked_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
