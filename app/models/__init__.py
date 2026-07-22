from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    discord_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    monitors: Mapped[list["Monitor"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    expected_status: Mapped[int] = mapped_column(Integer, default=200)
    expected_body_contains: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    public_slug: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    last_alert_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_ssl_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="monitors")
    checks: Mapped[list["CheckResult"]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="CheckResult.checked_at.desc()",
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        Index("ix_check_results_monitor_checked_at", "monitor_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    is_up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    monitor: Mapped["Monitor"] = relationship(back_populates="checks")
