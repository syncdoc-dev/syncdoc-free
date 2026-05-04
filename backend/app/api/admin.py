"""Admin system status endpoints"""

from datetime import datetime
from typing import Optional

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.setting import AppSetting

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


_start_time = datetime.now()


@router.get("/admin/status", response_model=AdminResponse)
async def get_system_status(
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive system status"""
    global _start_time
    _start_time = datetime.now()

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

        # Get stats
        sources_result = await db.execute(text("SELECT COUNT(*) FROM sources"))
        db_stats.total_sources = sources_result.scalar() or 0

        nodes_result = await db.execute(text("SELECT COUNT(*) FROM infra_nodes"))
        db_stats.total_nodes = nodes_result.scalar() or 0

        pages_result = await db.execute(text("SELECT COUNT(*) FROM doc_pages"))
        db_stats.total_pages = pages_result.scalar() or 0

        drift_result = await db.execute(
            text("SELECT COUNT(*) FROM drift_events WHERE resolved = 0")
        )
        db_stats.total_drift_events = drift_result.scalar() or 0

        sync_result = await db.execute(text("SELECT COUNT(*) FROM sync_runs"))
        db_stats.total_sync_runs = sync_result.scalar() or 0

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
        result = await db.execute(
            select(AppSetting).where(
                AppSetting.key.in_(
                    [
                        "slack_webhook_url",
                        "github_token",
                        "llm_api_key",
                        "openai_api_key",
                        "anthropic_api_key",
                    ]
                )
            )
        )
        rows = result.scalars().all()
        db_settings = {row.key: row.value for row in rows}
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
        timestamp=datetime.now().isoformat(),
        version=settings.app_version,
    )

    return AdminResponse(
        system=system,
        components=components,
        database_stats=db_stats,
        settings_summary=settings_summary,
    )


@router.get("/admin/db/tables")
async def list_tables(db: AsyncSession = Depends(get_db)):
    """List all database tables"""
    result = await db.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result.all()]
    return {"tables": tables}


@router.get("/admin/db/tables/{table}")
async def table_data(
    table: str, limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)
):
    """Get data from a specific table"""
    # Validate table name to prevent SQL injection
    result = await db.execute(
        text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :table
    """),
        {"table": table},
    )

    if not result.first():
        return {"error": f"Table '{table}' not found", "columns": [], "rows": []}

    # Get row count
    count_result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
    total = count_result.scalar() or 0

    # Get columns
    cols_result = await db.execute(
        text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :table
        ORDER BY ordinal_position
    """),
        {"table": table},
    )
    columns = [{"name": row[0], "type": row[1]} for row in cols_result.all()]

    # Get data with limit/offset
    data_result = await db.execute(
        text(f"SELECT * FROM {table} LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    )
    rows = [dict(row._mapping) for row in data_result.all()]

    return {
        "table": table,
        "total": total,
        "limit": limit,
        "offset": offset,
        "columns": columns,
        "rows": rows,
    }
