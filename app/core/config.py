from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://antipas:antipas@localhost:5432/antipas"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    firebase_credentials_path: str | None = None

    admin_secret_key: str = "change-me"

    listing_expiry_hours: int = 72


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
