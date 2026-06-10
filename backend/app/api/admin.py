"""Admin system status endpoints"""

from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.drift import DriftEvent
from app.models.node import InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.models.sync import SyncRun
from app.services.runtime_settings import get_runtime_settings

router = APIRouter()


class SystemStatus(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: Optional[float] = None
    version: str


class ComponentStatus(BaseModel):
    name: str
    status: str
    details: Optional[str] = None


class DbStats(BaseModel):
    total_sources: int
    total_nodes: int
    total_pages: int
    total_drift_events: int
    total_sync_runs: int


class AdminResponse(BaseModel):
    system: SystemStatus
    components: list[ComponentStatus]
    database_stats: DbStats
    settings_summary: dict


_start_time = datetime.now(timezone.utc)


@router.get("/admin/status", response_model=AdminResponse)
async def get_system_status(
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive system status"""
    settings = get_settings()
    components = []
    db_stats = DbStats(
        total_sources=0,
        total_nodes=0,
        total_pages=0,
        total_drift_events=0,
        total_sync_runs=0,
    )

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        components.append(ComponentStatus(name="database", status="healthy", details="Connected"))

        source_ids = select(Source.id).where(Source.organization_id == ctx.organization_id)
        node_ids = select(InfraNode.id).where(InfraNode.source_id.in_(source_ids))
        db_stats.total_sources = int(
            await db.scalar(
                select(func.count(Source.id)).where(Source.organization_id == ctx.organization_id)
            )
            or 0
        )
        db_stats.total_nodes = int(
            await db.scalar(
                select(func.count(InfraNode.id)).where(InfraNode.source_id.in_(source_ids))
            )
            or 0
        )
        db_stats.total_pages = int(
            await db.scalar(
                select(func.count(DocPage.id)).where(DocPage.organization_id == ctx.organization_id)
            )
            or 0
        )
        db_stats.total_drift_events = int(
            await db.scalar(
                select(func.count(DriftEvent.id)).where(
                    DriftEvent.node_id.in_(node_ids),
                    DriftEvent.resolved == 0,
                )
            )
            or 0
        )
        db_stats.total_sync_runs = int(
            await db.scalar(select(func.count(SyncRun.id)).where(SyncRun.source_id.in_(source_ids)))
            or 0
        )

    except Exception as e:
        components.append(ComponentStatus(name="database", status="unhealthy", details=str(e)))

    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        components.append(ComponentStatus(name="redis", status="healthy", details="Connected"))
    except Exception as e:
        components.append(ComponentStatus(name="redis", status="unhealthy", details=str(e)))

    # Check worker (via Celery inspect)
    try:
        from app.celery_app import app as celery_app

        i = celery_app.control.inspect(timeout=1)
        stats = i.stats()
        if stats:
            worker_count = len(stats)
            components.append(
                ComponentStatus(
                    name="worker", status="healthy", details=f"{worker_count} worker(s) running"
                )
            )
        else:
            components.append(
                ComponentStatus(name="worker", status="unhealthy", details="No active workers")
            )
    except Exception as e:
        components.append(ComponentStatus(name="worker", status="unhealthy", details=str(e)))

    # Settings summary (masked) - check both config file and database
    has_llm_key = bool(settings.llm_api_key)

    settings_summary = {
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "notification_type": settings.notification_type,
        "has_slack": bool(settings.slack_webhook_url),
        "has_github": bool(settings.github_token),
        "has_llm_api_key": has_llm_key,
        "jwt_algorithm": settings.jwt_algorithm,
    }

    # Also check database for runtime settings
    try:
        db_settings = await get_runtime_settings(
            db,
            ctx.organization_id,
            {
                "slack_webhook_url",
                "github_token",
                "llm_api_key",
                "openai_api_key",
                "anthropic_api_key",
            },
        )
        if db_settings.get("slack_webhook_url"):
            settings_summary["has_slack"] = True
        if db_settings.get("github_token"):
            settings_summary["has_github"] = True
        if (
            db_settings.get("llm_api_key")
            or db_settings.get("openai_api_key")
            or db_settings.get("anthropic_api_key")
        ):
            has_llm_key = True
        settings_summary["has_llm_api_key"] = has_llm_key
    except Exception:
        pass  # Table might not exist yet

    system = SystemStatus(
        status="running",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=(datetime.now(timezone.utc) - _start_time).total_seconds(),
        version=settings.app_version,
    )

    return AdminResponse(
        system=system,
        components=components,
        database_stats=db_stats,
        settings_summary=settings_summary,
    )
