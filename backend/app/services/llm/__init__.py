"""LLM provider factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.config import settings
from app.models.setting import AppSetting
from app.services.llm.base import LLMClient

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _load_effective_settings(
    db: AsyncSession | None,
) -> dict[str, str | None]:
    """Merge DB overrides on top of env defaults."""
    cfg: dict[str, str | None] = {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_endpoint_url": settings.llm_endpoint_url,
        "llm_api_key": settings.llm_api_key,
    }
    if db is not None:
        rows = (await db.execute(select(AppSetting))).scalars().all()
        legacy_llm_api_key: str | None = None
        for row in rows:
            if row.key in cfg:
                cfg[row.key] = row.value
            elif row.key in {"openai_api_key", "anthropic_api_key"} and row.value:
                legacy_llm_api_key = row.value
        if not cfg["llm_api_key"] and legacy_llm_api_key:
            cfg["llm_api_key"] = legacy_llm_api_key
    return cfg


async def get_llm_client(db: AsyncSession | None = None) -> LLMClient:
    """Return the configured LLM client, reading DB overrides when available."""
    cfg = await _load_effective_settings(db)
    base_url = cfg["llm_endpoint_url"] or None

    if cfg["llm_provider"] == "openai":
        from app.services.llm.openai import OpenAIClient

        if not cfg["llm_api_key"]:
            raise ValueError("LLM_API_KEY is required when llm_provider=openai")
        return OpenAIClient(
            api_key=cfg["llm_api_key"],
            model=cfg["llm_model"] or "gpt-4o",
            base_url=base_url,
        )

    from app.services.llm.anthropic import AnthropicClient

    if not cfg["llm_api_key"]:
        raise ValueError("LLM_API_KEY is required when llm_provider=anthropic")
    return AnthropicClient(
        api_key=cfg["llm_api_key"],
        model=cfg["llm_model"] or "claude-sonnet-4-20250514",
        base_url=base_url,
    )


__all__ = ["LLMClient", "get_llm_client"]
