"""Redis-backed sync event publishing and WebSocket streaming."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


def _channel_name(organization_id: str) -> str:
    return f"sync-events:{organization_id}"


async def publish_sync_event(organization_id: str, event: dict[str, Any]) -> None:
    """Publish a sync-related event for one organization."""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        payload = json.dumps(event, default=str)
        await client.publish(_channel_name(organization_id), payload)
    except Exception:
        logger.exception("Failed to publish sync event")
    finally:
        await client.close()


async def subscribe_sync_events(organization_id: str) -> AsyncIterator[dict[str, Any]]:
    """Subscribe to sync-related events for one organization."""
    client = redis.from_url(settings.redis_url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(_channel_name(organization_id))
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if not message:
                yield {"type": "ping"}
                continue

            data = message.get("data")
            if not isinstance(data, str):
                continue
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed sync event payload")
    finally:
        await pubsub.unsubscribe(_channel_name(organization_id))
        await pubsub.close()
        await client.close()
