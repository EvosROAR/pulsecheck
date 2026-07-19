from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PulseCheck"
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    database_url: str = "sqlite+aiosqlite:///./pulsecheck.db"
    check_timeout_seconds: float = 10.0
    default_interval_seconds: int = 60
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
