"""Settings API: runtime application configuration."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.setting import AppSetting
from app.schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter()

DEFAULT_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}

# Keys that contain secrets and should be masked in responses
_SECRET_KEYS = {
    "llm_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "slack_webhook_url",
    "github_token",
}

# All known setting keys and their config.py attribute names
_SETTING_KEYS = [
    "llm_provider",
    "llm_model",
    "llm_endpoint_url",
    "llm_api_key",
    "notification_type",
    "slack_webhook_url",
    "github_token",
    "auto_sync_enabled",
    "auto_sync_interval_minutes",
]


def _mask(value: str | None) -> str | None:
    """Mask a secret, showing only the last 4 characters."""
    if not value:
        return None
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


def _is_masked(value: str | None) -> bool:
    """Check if a value is a masked placeholder."""
    return bool(value and value.startswith("••••"))


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Return current settings (secrets masked)."""
    # Load DB overrides
    rows = (await db.execute(select(AppSetting))).scalars().all()
    db_values = {row.key: row.value for row in rows}

    # Build response: DB value > env default
    provider = db_values.get("llm_provider", app_settings.llm_provider)
    endpoint = db_values.get(
        "llm_endpoint_url",
        app_settings.llm_endpoint_url or DEFAULT_ENDPOINTS.get(provider, ""),
    )

    def _bool(key: str, default: bool) -> bool:
        v = db_values.get(key)
        if v is None:
            return default
        return v.lower() in ("true", "1", "yes", "on")

    def _int(key: str, default: int) -> int:
        v = db_values.get(key)
        if v is None:
            return default
        try:
            return int(v)
        except ValueError:
            return default

    return SettingsResponse(
        llm_provider=provider,
        llm_model=db_values.get("llm_model", app_settings.llm_model),
        llm_endpoint_url=endpoint,
        llm_api_key=_mask(
            db_values.get(
                "llm_api_key",
                db_values.get("openai_api_key")
                or db_values.get("anthropic_api_key")
                or app_settings.llm_api_key,
            )
        ),
        notification_type=db_values.get("notification_type", app_settings.notification_type),
        slack_webhook_url=_mask(db_values.get("slack_webhook_url", app_settings.slack_webhook_url)),
        github_token=_mask(db_values.get("github_token", app_settings.github_token)),
        auto_sync_enabled=_bool("auto_sync_enabled", True),
        auto_sync_interval_minutes=_int("auto_sync_interval_minutes", 5),
    )


@router.put("/", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update settings. Masked values are ignored. Returns updated settings."""
    changes = updates.model_dump(exclude_none=True)

    for key, value in changes.items():
        # Skip masked placeholders sent back by the frontend
        if key in _SECRET_KEYS and _is_masked(value):
            continue

        # Coerce booleans/ints to strings for the key-value store
        store_value = str(value) if value is not None else ""

        # Upsert into DB
        existing = await db.get(AppSetting, key)
        if existing:
            existing.value = store_value
        else:
            db.add(AppSetting(key=key, value=store_value))

        # Patch in-memory settings so changes take effect immediately
        if hasattr(app_settings, key):
            object.__setattr__(app_settings, key, value)

    await db.commit()

    # Return the refreshed settings
    return await get_settings(ctx, db)
