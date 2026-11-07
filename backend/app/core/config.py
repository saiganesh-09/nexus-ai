from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "NEXUS AI"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"

    database_url: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    request_timeout_seconds: float = 30.0
    max_request_body_bytes: int = 1_000_000

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
