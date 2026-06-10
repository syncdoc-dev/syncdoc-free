"""Slack notification service for drift alerts and workflow events."""

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.runtime_settings import get_runtime_settings

logger = logging.getLogger(__name__)


async def _get_runtime_setting(
    key: str,
    db: AsyncSession | None = None,
    organization_id: str | None = None,
) -> str | None:
    if db is not None and organization_id and settings.allow_runtime_settings:
        values = await get_runtime_settings(db, organization_id, {key})
        if values.get(key):
            return values[key]
    return getattr(settings, key, None)


async def _get_notification_config(
    db: AsyncSession | None = None,
    organization_id: str | None = None,
) -> tuple[str | None, str | None]:
    notification_type = await _get_runtime_setting("notification_type", db, organization_id)
    webhook_url = await _get_runtime_setting("slack_webhook_url", db, organization_id)
    return notification_type, webhook_url


async def send_drift_alert(
    source_name: str,
    drift_events: list[dict[str, Any]],
    *,
    db: AsyncSession | None = None,
    organization_id: str | None = None,
) -> bool:
    """Post a drift alert to Slack via incoming webhook.

    Returns True if the message was sent successfully.
    """
    notification_type, webhook_url = await _get_notification_config(db, organization_id)
    if notification_type not in (None, "", "slack"):
        logger.debug("Notification type is %s — skipping Slack notification", notification_type)
        return False
    if not webhook_url:
        logger.debug("No Slack webhook configured — skipping notification")
        return False

    count = len(drift_events)
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Drift Detected — {source_name}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{count}* resource{'s' if count != 1 else ''} changed during sync.",
            },
        },
        {"type": "divider"},
    ]

    for event in drift_events[:10]:
        node_name = event.get("node_name", "unknown")
        node_kind = event.get("node_kind", "")
        diff = event.get("diff", {})
        changes = []
        for section in ("added", "removed", "changed"):
            keys = diff.get(section, {})
            if keys:
                changes.append(f"_{section}_: {', '.join(str(k) for k in keys.keys())}")

        summary = "\n".join(changes) if changes else "config changed"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{node_name}* (`{node_kind}`)\n{summary}",
                },
            }
        )

    if count > 10:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_...and {count - 10} more_",
                    }
                ],
            }
        )

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info("Slack drift alert sent for %s (%d events)", source_name, count)
            return True
    except httpx.HTTPError as exc:
        logger.error("Failed to send Slack notification: %s", exc)
        return False


async def send_workflow_notification(
    workflow: Any,
    page: Any,
    action: str,
    *,
    db: AsyncSession | None = None,
    organization_id: str | None = None,
) -> bool:
    """Post a workflow event notification to Slack via incoming webhook.

    Returns True if the message was sent successfully.
    """
    notification_type, webhook_url = await _get_notification_config(db, organization_id)
    if notification_type not in (None, "", "slack"):
        logger.debug("Notification type is %s — skipping Slack notification", notification_type)
        return False
    if not webhook_url:
        logger.debug("No Slack webhook configured — skipping notification")
        return False

    action_messages = {
        "submit_for_review": "submitted for review",
        "start_review": "started review",
        "approve": "approved",
        "publish": "published",
        "reject": "rejected",
        "archive": "archived",
        "reopen": "reopened",
    }

    message = action_messages.get(action, action)
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Page {message}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{page.title}*\nStatus: `{workflow.state}`",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Page ID: {page.id}",
                }
            ],
        },
    ]

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info("Slack workflow notification sent for page %s (%s)", page.id, action)
            return True
    except httpx.HTTPError as exc:
        logger.error("Failed to send workflow Slack notification: %s", exc)
        return False
