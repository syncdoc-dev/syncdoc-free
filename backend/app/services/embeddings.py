"""Embedding generation using the configured LLM endpoint."""

import logging
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import _load_effective_settings

logger = logging.getLogger(__name__)


async def get_embedding(text: str, db: Optional[AsyncSession] = None) -> list[float] | None:
    """Generate embeddings. Uses OpenAI API or custom LLM endpoint if configured."""
    try:
        cfg = await _load_effective_settings(db)
        api_key = cfg.get("llm_api_key")
        base_url = cfg.get("llm_endpoint_url")

        # If no API key, can't proceed
        if not api_key:
            return None
        # Default model depends on endpoint
        if base_url:
            # Custom endpoint (e.g., LM Studio)
            model = cfg.get("embedding_model") or "text-embedding-nomic-embed-text-v1.5"
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            # Use OpenAI directly (text-embedding-3-small returns 1536 dimensions)
            model = cfg.get("embedding_model") or "text-embedding-3-small"
            client = AsyncOpenAI(api_key=api_key)

            response = await client.embeddings.create(model=model, input=text[:8000])
        return response.data[0].embedding
    except Exception as exc:
        logger.warning("Embedding generation failed: %s", exc)
        return None
