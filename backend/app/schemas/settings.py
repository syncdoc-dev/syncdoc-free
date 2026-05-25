"""Settings schema models"""

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    """Settings response — API keys are masked."""

    llm_provider: str
    llm_model: str
    llm_endpoint_url: str
    llm_api_key: str | None = None
    notification_type: str | None = None
    slack_webhook_url: str | None = None
    github_token: str | None = None
    auto_sync_enabled: bool = True
    auto_sync_interval_minutes: int = 5


class SettingsUpdate(BaseModel):
    """Partial settings update."""

    llm_provider: str | None = None
    llm_model: str | None = None
    llm_endpoint_url: str | None = None
    llm_api_key: str | None = None
    notification_type: str | None = None
    slack_webhook_url: str | None = None
    github_token: str | None = None
    auto_sync_enabled: bool | None = None
    auto_sync_interval_minutes: int | None = None
