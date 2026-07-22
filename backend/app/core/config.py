"""Core configuration - environment variables and settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: Literal["development", "staging", "production"] = "development"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/webpulse"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-2024-08-06"

    clickup_api_token: str = ""
    clickup_list_id: str = ""

    calendly_api_token: str = ""
    calendly_event_type_uri: str = ""
    calendly_webhook_signing_key: str = ""

    resend_api_key: str = ""
    email_from: str = "WebPulse <reports@webpulsehq.com>"

    jwt_secret: str = "dev-only-change-me"
    recaptcha_secret: str = ""

    rate_limit_per_ip: int = 3
    rate_limit_per_email: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
