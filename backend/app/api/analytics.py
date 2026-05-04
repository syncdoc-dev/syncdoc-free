"""Analytics API endpoints"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.drift import DriftEvent
from app.models.page import DocPage
from app.models.source import Source
from app.models.sync import SyncRun
from app.services.capabilities import Capability, require_capability

router = APIRouter()


class UsageStats(BaseModel):
    total_sources: int
    total_nodes: int
    total_pages: int
    total_drift_events: int
    total_sync_runs: int
    pages_created_this_week: int
    sources_synced_this_week: int
    drift_events_this_week: int


class SyncFrequencyPoint(BaseModel):
    date: str
    count: int
    successful: int
    failed: int
    nodes_added: int
    nodes_updated: int


class DriftTrendPoint(BaseModel):
    date: str
    detected: int
    resolved: int


class SourceCoverage(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    node_count: int
    page_count: int
    last_synced: Optional[str]
    drift_count: int


class PageCoverageStats(BaseModel):
    total_pages: int
    pages_with_source: int
    manually_edited: int
    auto_generated: int
    sources: list[SourceCoverage]


class AnalyticsResponse(BaseModel):
    usage_stats: UsageStats
    sync_frequency: list[SyncFrequencyPoint]
    drift_trends: list[DriftTrendPoint]
    page_coverage: PageCoverageStats


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    project_id: Optional[str] = Query(None),
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive analytics data"""
    await require_capability(ctx.organization_id, Capability.ANALYTICS, db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    week_ago = now - timedelta(days=7)
    resolved_project_id = await resolve_project_id(project_id, ctx, db)

    # Usage stats using SQLAlchemy ORM
    sources_result = await db.execute(
        select(func.count(Source.id)).where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    total_sources = sources_result.scalar() or 0

    from app.models.node import InfraNode

    nodes_result = await db.execute(
        select(func.count(InfraNode.id))
        .join(Source, InfraNode.source_id == Source.id)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    total_nodes = nodes_result.scalar() or 0

    pages_result = await db.execute(
        select(func.count(DocPage.id)).where(
            DocPage.organization_id == ctx.organization_id,
            DocPage.project_id == resolved_project_id,
        )
    )
    total_pages = pages_result.scalar() or 0

    drift_result = await db.execute(
        select(func.count(DriftEvent.id))
        .join(InfraNode, DriftEvent.node_id == InfraNode.id)
        .join(Source, InfraNode.source_id == Source.id)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    total_drift_events = drift_result.scalar() or 0

    sync_result = await db.execute(
        select(func.count(SyncRun.id))
        .join(Source, SyncRun.source_id == Source.id)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    total_sync_runs = sync_result.scalar() or 0

    # Use ORM queries with datetime comparison
    pages_this_week_result = await db.execute(
        select(func.count(DocPage.id)).where(
            DocPage.created_at >= week_ago,
            DocPage.organization_id == ctx.organization_id,
            DocPage.project_id == resolved_project_id,
        )
    )
    pages_created_this_week = pages_this_week_result.scalar() or 0

    sources_this_week_result = await db.execute(
        select(func.count(func.distinct(SyncRun.source_id)))
        .join(Source, SyncRun.source_id == Source.id)
        .where(
            SyncRun.started_at >= week_ago,
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    sources_synced_this_week = sources_this_week_result.scalar() or 0

    drift_this_week_result = await db.execute(
        select(func.count(DriftEvent.id))
        .join(InfraNode, DriftEvent.node_id == InfraNode.id)
        .join(Source, InfraNode.source_id == Source.id)
        .where(
            DriftEvent.detected_at >= week_ago,
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    drift_events_this_week = drift_this_week_result.scalar() or 0

    usage_stats = UsageStats(
        total_sources=total_sources,
        total_nodes=total_nodes,
        total_pages=total_pages,
        total_drift_events=total_drift_events,
        total_sync_runs=total_sync_runs,
        pages_created_this_week=pages_created_this_week,
        sources_synced_this_week=sources_synced_this_week,
        drift_events_this_week=drift_events_this_week,
    )

    # Sync frequency (time series) - use raw SQL with proper parameter handling
    sync_frequency: list[SyncFrequencyPoint] = []
    sync_series_result = await db.execute(
        text("""
            SELECT
                DATE(sr.started_at) as date,
                COUNT(*) as count,
                SUM(CASE WHEN sr.status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN sr.status = 'failed' THEN 1 ELSE 0 END) as failed,
                COALESCE(SUM(sr.nodes_added), 0) as nodes_added,
                COALESCE(SUM(sr.nodes_updated), 0) as nodes_updated
            FROM sync_runs sr
            JOIN sources s ON s.id = sr.source_id
            WHERE sr.started_at >= :start AND sr.started_at < :end
              AND s.organization_id = :org_id
              AND s.project_id = :project_id
            GROUP BY DATE(sr.started_at)
            ORDER BY date
        """),
        {
            "start": start,
            "end": now,
            "org_id": ctx.organization_id,
            "project_id": resolved_project_id,
        },
    )
    for row in sync_series_result.all():
        sync_frequency.append(
            SyncFrequencyPoint(
                date=str(row.date),
                count=int(row._mapping["count"]),
                successful=int(row._mapping["successful"] or 0),
                failed=int(row._mapping["failed"] or 0),
                nodes_added=int(row._mapping["nodes_added"]),
                nodes_updated=int(row._mapping["nodes_updated"]),
            )
        )

    # Drift trends (time series)
    drift_trends: list[DriftTrendPoint] = []
    drift_series_result = await db.execute(
        text("""
            SELECT
                DATE(d.detected_at) as date,
                COUNT(*) as detected,
                SUM(CASE WHEN d.resolved = 1 THEN 1 ELSE 0 END) as resolved
            FROM drift_events d
            JOIN infra_nodes n ON n.id = d.node_id
            JOIN sources s ON s.id = n.source_id
            WHERE d.detected_at >= :start AND d.detected_at < :end
              AND s.organization_id = :org_id
              AND s.project_id = :project_id
            GROUP BY DATE(d.detected_at)
            ORDER BY date
        """),
        {
            "start": start,
            "end": now,
            "org_id": ctx.organization_id,
            "project_id": resolved_project_id,
        },
    )
    for row in drift_series_result.all():
        drift_trends.append(
            DriftTrendPoint(
                date=str(row.date),
                detected=row.detected,
                resolved=int(row.resolved or 0),
            )
        )

    # Page coverage by source - use raw SQL for complex aggregation
    coverage_result = await db.execute(
        text("""
            SELECT
                s.id as source_id,
                s.url as source_name,
                s.type as source_type,
                s.last_synced,
                COUNT(DISTINCT n.id) as node_count,
                COUNT(DISTINCT p.id) as page_count,
                COUNT(DISTINCT d.id) as drift_count
            FROM sources s
            LEFT JOIN infra_nodes n ON n.source_id = s.id
            LEFT JOIN doc_pages p ON p.source_id = s.id
            LEFT JOIN drift_events d ON d.node_id = n.id
            WHERE s.organization_id = :org_id
              AND s.project_id = :project_id
            GROUP BY s.id, s.url, s.type, s.last_synced
            ORDER BY s.created_at
        """),
        {"org_id": ctx.organization_id, "project_id": resolved_project_id},
    )

    source_coverages: list[SourceCoverage] = []
    for row in coverage_result.all():
        last_synced = row[3]
        source_coverages.append(
            SourceCoverage(
                source_id=row[0],
                source_name=row[1],
                source_type=row[2],
                last_synced=last_synced.isoformat() if last_synced else None,
                node_count=row[4],
                page_count=row[5],
                drift_count=row[6],
            )
        )

    # Page coverage stats
    pages_with_source_result = await db.execute(
        select(func.count(DocPage.id)).where(
            DocPage.source_id.isnot(None),
            DocPage.organization_id == ctx.organization_id,
            DocPage.project_id == resolved_project_id,
        )
    )
    pages_with_source = pages_with_source_result.scalar() or 0

    manually_edited_result = await db.execute(
        select(func.count(DocPage.id)).where(
            DocPage.is_manually_edited == 1,
            DocPage.organization_id == ctx.organization_id,
            DocPage.project_id == resolved_project_id,
        )
    )
    manually_edited = manually_edited_result.scalar() or 0

    page_coverage = PageCoverageStats(
        total_pages=total_pages,
        pages_with_source=pages_with_source,
        manually_edited=manually_edited,
        auto_generated=total_pages - manually_edited,
        sources=source_coverages,
    )

    return AnalyticsResponse(
        usage_stats=usage_stats,
        sync_frequency=sync_frequency,
        drift_trends=drift_trends,
        page_coverage=page_coverage,
    )
