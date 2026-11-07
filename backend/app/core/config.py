from functools import lru_cache

from pydantic import field_validator
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

    # Comma-separated list, e.g. "http://localhost:3000,https://app.example.com"
    cors_origins: str = "http://localhost:3000"
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    request_timeout_seconds: float = 30.0
    provider_max_retries: int = 2
    retry_base_delay_seconds: float = 0.5
    cache_ttl_seconds: int = 3600
    max_request_body_bytes: int = 1_000_000

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com"
    # Generic OpenAI-compatible endpoint (Ollama, Groq, LM Studio...).
    # Keyless endpoints are supported — leave the key empty for local models.
    openai_compat_base_url: str = "http://localhost:11434/v1"
    openai_compat_api_key: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        # Managed hosts (Render, Railway...) hand out postgres:// or
        # postgresql:// URLs; the async engine requires the asyncpg driver.
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
            elif v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
