from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET = "change-me"
# HMAC-SHA256 wants >=32 bytes (RFC 7518 §3.2); a short key makes PyJWT warn on every call. This
# default only exists so local dev runs without setup — the validator below rejects it in prod.
INSECURE_JWT_SECRET = "dev-only-insecure-jwt-signing-key-change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    api_v1_prefix: str = "/api/v1"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    database_url: str = "postgresql+asyncpg://antipas:antipas@localhost:5432/antipas"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    firebase_credentials_path: str | None = None

    admin_secret_key: str = INSECURE_SECRET

    # JWT auth. No refresh token yet, so the access token is long-lived by design (see
    # app/core/security.py). Shorten it once a refresh flow exists.
    jwt_secret_key: str = INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    listing_expiry_hours: int = 72

    @model_validator(mode="after")
    def _refuse_default_secrets_in_production(self) -> "Settings":
        """A shipped default signing key would let anyone mint a token for any user."""
        if self.is_production:
            defaulted = [
                name
                for name, insecure in (
                    ("jwt_secret_key", INSECURE_JWT_SECRET),
                    ("admin_secret_key", INSECURE_SECRET),
                )
                if getattr(self, name) == insecure
            ]
            if defaulted:
                raise ValueError(
                    f"ENVIRONMENT=production requires real secrets; still defaulted: {', '.join(defaulted)}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
