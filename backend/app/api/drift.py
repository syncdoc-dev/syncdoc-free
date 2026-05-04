"""Drift events API endpoints"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.drift import DriftEvent
from app.models.node import InfraNode
from app.models.source import Source
from app.schemas.drift import DriftEventResponse, DriftResolve

router = APIRouter()


@router.get("/", response_model=List[DriftEventResponse])
async def list_drift_events(
    source_id: Optional[str] = Query(None),
    resolved: Optional[int] = Query(None, description="0=unresolved, 1=resolved"),
    project_id: Optional[str] = Query(None),
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """List drift events, optionally filtered by source and resolution status"""
    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    query = (
        select(DriftEvent, InfraNode.name, InfraNode.kind)
        .join(InfraNode, DriftEvent.node_id == InfraNode.id)
        .join(Source, InfraNode.source_id == Source.id)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
        .order_by(DriftEvent.detected_at.desc())
    )

    if source_id:
        query = query.where(InfraNode.source_id == source_id)
    if resolved is not None:
        query = query.where(DriftEvent.resolved == resolved)

    result = await db.execute(query)
    rows = result.all()

    return [
        DriftEventResponse(
            id=event.id,
            node_id=event.node_id,
            node_name=node_name,
            node_kind=node_kind,
            page_id=event.page_id,
            detected_at=event.detected_at,
            diff_json=event.diff_json,
            resolved=event.resolved,
            resolved_at=event.resolved_at,
            resolution_notes=event.resolution_notes,
            created_at=event.created_at,
        )
        for event, node_name, node_kind in rows
    ]


@router.get("/stats")
async def drift_stats(
    project_id: Optional[str] = Query(None),
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get drift event statistics"""
    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    all_events = await db.execute(
        select(DriftEvent)
        .join(InfraNode, DriftEvent.node_id == InfraNode.id)
        .join(Source, InfraNode.source_id == Source.id)
        .where(
            Source.organization_id == ctx.organization_id,
            Source.project_id == resolved_project_id,
        )
    )
    events = all_events.scalars().all()

    unresolved = sum(1 for e in events if e.resolved == 0)
    resolved = sum(1 for e in events if e.resolved == 1)

    return {
        "total": len(events),
        "unresolved": unresolved,
        "resolved": resolved,
    }


@router.post("/{drift_id}/resolve", response_model=DriftEventResponse)
async def resolve_drift_event(
    drift_id: str,
    body: DriftResolve,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Mark a drift event as resolved"""
    event = await db.get(DriftEvent, drift_id)
    if not event:
        raise HTTPException(status_code=404, detail="Drift event not found")
    node = await db.get(InfraNode, event.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Drift event not found")
    source = await db.get(Source, node.source_id)
    if not source or source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Drift event not found")

    event.resolved = 1
    event.resolved_at = datetime.now(timezone.utc)
    if body.resolution_notes:
        event.resolution_notes = body.resolution_notes

    await db.commit()
    await db.refresh(event)

    return DriftEventResponse(
        id=event.id,
        node_id=event.node_id,
        node_name=node.name if node else None,
        node_kind=node.kind if node else None,
        page_id=event.page_id,
        detected_at=event.detected_at,
        diff_json=event.diff_json,
        resolved=event.resolved,
        resolved_at=event.resolved_at,
        resolution_notes=event.resolution_notes,
        created_at=event.created_at,
    )
