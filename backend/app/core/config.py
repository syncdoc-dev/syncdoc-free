"""Application configuration"""

import os

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env if it exists (local dev)
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Database
    database_url: str = "postgresql+asyncpg://syncdoc:syncdoc_dev@localhost:5432/syncdoc"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Environment
    environment: str = "development"

    # API
    api_title: str = "SyncDoc API"
    # App version from Docker build arg (format: "v0.1.0" for releases, "dev-abc123" for dev)
    app_version: str = os.getenv("APP_VERSION", "dev")

    # LLM
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4o"
    llm_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_ENDPOINT_URL", "LLM_BASE_URL"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"),
    )

    # Notifications
    notification_type: str = "slack"
    slack_webhook_url: str | None = None
    github_token: str | None = None

    # GitHub OAuth
    # GH_ prefix used in Doppler/env because GITHUB_ is reserved by GitHub Actions
    github_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GH_CLIENT_ID", "GITHUB_CLIENT_ID"),
    )
    github_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("GH_CLIENT_SECRET", "GITHUB_CLIENT_SECRET"),
    )

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # URLs
    frontend_url: str = "http://localhost:5174"
    backend_url: str = "http://localhost:8000"

    # Registration
    allow_self_register: bool = True
    bootstrap_token: str | None = None

    # Email / SMTP
    email_enabled: bool = False
    email_provider: str = "smtp"
    email_from_address: str = Field(
        default="no-reply@syncdoc.dev",
        validation_alias=AliasChoices("EMAIL_FROM_ADDRESS", "EMAIL_FROM"),
    )
    email_from_name: str = "SyncDoc"
    email_reply_to: str | None = None
    registration_notify_to: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    password_reset_expire_minutes: int = 60

    # Licensing
    license_public_key: str | None = None
    license_enforcement_enabled: bool = False
    license_allow_unsigned_dev: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()
