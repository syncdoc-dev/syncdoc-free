"""Sources API endpoints"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import list_connectors
from app.connectors.exceptions import PullError
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.drift import DriftEvent
from app.models.node import InfraEdge, InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.models.sync import SyncRun
from app.schemas.source import (
    SourceCreate,
    SourceInspectionResponse,
    SourceInspectRequest,
    SourceResponse,
)
from app.services.entitlements import LIMIT_SOURCES, assert_limit, count_sources
from app.services.source_inspection import inspect_source

router = APIRouter()


class SyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    nodes_added: int
    nodes_updated: int
    drift_count: int
    error_message: Optional[str]


class SyncRunWithSource(SyncRunResponse):
    source_name: Optional[str] = None
    source_type: Optional[str] = None


@router.post("/", response_model=SourceResponse, status_code=201)
async def create_source(
    source: SourceCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Register a new IaC source"""
    await assert_limit(
        ctx.organization_id,
        LIMIT_SOURCES,
        await count_sources(ctx.organization_id, db),
        db,
    )
    valid_types = list_connectors()
    if source.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source type '{source.type}'. Valid: {valid_types}",
        )

    try:
        inspection = await inspect_source(source.type, source.url, db)
    except PullError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to inspect source before adding it: {exc}",
        ) from exc
    if not inspection.ok:
        raise HTTPException(status_code=400, detail=inspection.summary)

    project_id = await resolve_project_id(source.project_id, ctx, db)
    db_source = Source(
        id=uuid.uuid4().hex[:16],
        type=source.type,
        url=source.url,
        credentials_ref=source.credentials_ref,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        project_id=project_id,
    )
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)
    return db_source


@router.post("/inspect", response_model=SourceInspectionResponse)
async def inspect_source_endpoint(
    payload: SourceInspectRequest,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    valid_types = list_connectors()
    if payload.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source type '{payload.type}'. Valid: {valid_types}",
        )

    try:
        inspection = await inspect_source(payload.type, payload.url, db)
    except PullError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SourceInspectionResponse(
        source_type=inspection.source_type,
        ok=inspection.ok,
        summary=inspection.summary,
        matched_files=inspection.matched_files,
        detected_types=inspection.detected_types,
        warnings=inspection.warnings,
    )


@router.get("/", response_model=List[SourceResponse])
async def list_sources(
    project_id: str | None = None,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """List all registered sources"""
    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    result = await db.execute(
        select(Source)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
        .order_by(Source.created_at.desc())
    )
    return result.scalars().all()


@router.get("/sync-runs", response_model=List[SyncRunWithSource])
async def list_all_sync_runs(
    limit: int = 50,
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    project_id: str | None = None,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
) -> List[SyncRunWithSource]:
    """Return sync runs across all sources (audit log), ordered by started_at descending"""
    query = select(SyncRun).order_by(SyncRun.started_at.desc()).limit(limit)

    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    source_query = select(Source.id).where(
        Source.organization_id == ctx.organization_id, Source.project_id == resolved_project_id
    )
    if source_id:
        source_query = source_query.where(Source.id == source_id)
    query = query.where(SyncRun.source_id.in_(source_query))
    if status:
        query = query.where(SyncRun.status == status)

    result = await db.execute(query)
    runs = list(result.scalars().all())

    response = []
    for run in runs:
        run_data = SyncRunWithSource(
            id=run.id,
            source_id=run.source_id,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            nodes_added=run.nodes_added,
            nodes_updated=run.nodes_updated,
            drift_count=run.drift_count,
            error_message=run.error_message,
            source_name=None,
            source_type=None,
        )
        response.append(run_data)

    return response


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific source"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a source and all related records"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    # Get node IDs for this source (needed for edges and drift events)
    node_result = await db.execute(select(InfraNode.id).where(InfraNode.source_id == source_id))
    node_ids = [row[0] for row in node_result.all()]

    if node_ids:
        # Delete drift events referencing these nodes
        await db.execute(delete(DriftEvent).where(DriftEvent.node_id.in_(node_ids)))
        # Delete edges referencing these nodes
        await db.execute(
            delete(InfraEdge).where(
                InfraEdge.from_node_id.in_(node_ids) | InfraEdge.to_node_id.in_(node_ids)
            )
        )
        # Delete nodes
        await db.execute(delete(InfraNode).where(InfraNode.source_id == source_id))

    # Delete doc pages for this source
    await db.execute(delete(DocPage).where(DocPage.source_id == source_id))
    # Delete sync runs for this source
    await db.execute(delete(SyncRun).where(SyncRun.source_id == source_id))
    # Delete the source itself
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/sync")
async def trigger_sync(
    source_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger manual sync for a source"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    from app.tasks.sync import sync_source

    task = sync_source.delay(source_id)
    return {"status": "sync_queued", "source_id": source_id, "task_id": task.id}


@router.get("/{source_id}/sync-runs", response_model=List[SyncRunResponse])
async def list_sync_runs(
    source_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
) -> List[SyncRun]:
    """Return the last 5 sync runs for a specific source"""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    result = await db.execute(
        select(SyncRun)
        .where(SyncRun.source_id == source_id)
        .order_by(SyncRun.started_at.desc())
        .limit(5)
    )
    return list(result.scalars().all())
