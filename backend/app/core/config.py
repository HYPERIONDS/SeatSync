from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    secret_key: str = "development-secret-change-me-at-least-32-chars"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    database_url: str = "postgresql+psycopg://seatsync:seatsync@localhost:5432/seatsync"
    test_database_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    test_redis_url: str = "redis://localhost:6379/15"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "no-reply@seatsync.local"
    frontend_origin: str = "http://localhost:5173"
    hold_ttl_seconds: int = Field(default=300, ge=1, le=900)
    cancellation_cutoff_hours: int = Field(default=24, ge=0)
    export_directory: Path = Path("exports")


@lru_cache
def get_settings() -> Settings:
    return Settings()
