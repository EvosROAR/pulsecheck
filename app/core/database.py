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


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema)
