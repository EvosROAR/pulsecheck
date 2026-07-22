from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings, normalize_database_url


class Base(DeclarativeBase):
    pass


settings = get_settings()
DATABASE_URL = normalize_database_url(settings.database_url)
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def _migrate_schema(connection) -> None:
    """Apply lightweight additive migrations for existing databases."""
    inspector = inspect(connection)
    tables = inspector.get_table_names()

    if "users" in tables:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "discord_webhook_url" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN discord_webhook_url VARCHAR(500)"))

    if "check_results" in tables:
        columns = {column["name"] for column in inspector.get_columns("check_results")}
        if "details_json" not in columns:
            connection.execute(text("ALTER TABLE check_results ADD COLUMN details_json TEXT"))

    if "monitors" in tables:
        columns = {column["name"] for column in inspector.get_columns("monitors")}
        if "expected_body_contains" not in columns:
            connection.execute(text("ALTER TABLE monitors ADD COLUMN expected_body_contains VARCHAR(200)"))
        if "public_slug" not in columns:
            connection.execute(text("ALTER TABLE monitors ADD COLUMN public_slug VARCHAR(32)"))
            try:
                connection.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_monitors_public_slug ON monitors (public_slug)")
                )
            except Exception:  # noqa: BLE001 - sqlite/postgres dialect differences
                pass
        if "last_alert_kind" not in columns:
            connection.execute(text("ALTER TABLE monitors ADD COLUMN last_alert_kind VARCHAR(32)"))
        if "last_alert_at" not in columns:
            connection.execute(text("ALTER TABLE monitors ADD COLUMN last_alert_at TIMESTAMP"))
        if "last_ssl_alert_at" not in columns:
            connection.execute(text("ALTER TABLE monitors ADD COLUMN last_ssl_alert_at TIMESTAMP"))

    if "check_results" in tables:
        try:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_check_results_monitor_checked_at "
                    "ON check_results (monitor_id, checked_at)"
                )
            )
        except Exception:  # noqa: BLE001
            pass


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema)
