"""Graph API endpoints: nodes/edges plus user annotations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.graph_edge_manual import GraphEdgeManual
from app.models.graph_note import GraphNote
from app.models.node import InfraEdge, InfraNode
from app.models.source import Source
from app.services.capabilities import Capability, require_capability
from app.tasks.sync import sync_source

router = APIRouter()


class GraphNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    pos_x: float
    pos_y: float
    from_node_id: str | None = None
    to_node_id: str | None = None
    source_id: str | None = None


class GraphNoteUpdate(BaseModel):
    content: str | None = Field(None, min_length=1, max_length=2000)
    pos_x: float | None = None
    pos_y: float | None = None


class ManualEdgeCreate(BaseModel):
    from_node_id: str
    to_node_id: str
    label: str | None = None
    color: str | None = None


class ManualEdgeUpdate(BaseModel):
    label: str | None = None
    color: str | None = None


async def _resolve_note_scope(
    payload: GraphNoteCreate, ctx: CurrentContext, db: AsyncSession
) -> tuple[str, str | None]:
    resolved_project_id = await resolve_project_id(None, ctx, db)
    source_id = payload.source_id

    from_node = await db.get(InfraNode, payload.from_node_id) if payload.from_node_id else None
    to_node = await db.get(InfraNode, payload.to_node_id) if payload.to_node_id else None

    for node in (from_node, to_node):
        if node and node.source_id:
            source_id = source_id or node.source_id
            source = await db.get(Source, node.source_id)
            if not source or source.organization_id != ctx.organization_id:
                raise HTTPException(status_code=404, detail="Node not found")
            resolved_project_id = source.project_id or resolved_project_id

    if source_id:
        source = await db.get(Source, source_id)
        if not source or source.organization_id != ctx.organization_id:
            raise HTTPException(status_code=404, detail="Source not found")
        resolved_project_id = source.project_id or resolved_project_id

    return resolved_project_id, source_id


@router.get("/")
async def get_graph(
    source_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Return the full node/edge graph, optionally filtered by source."""
    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    source_query = select(Source.id).where(
        Source.organization_id == ctx.organization_id, Source.project_id == resolved_project_id
    )
    if source_id:
        source_query = source_query.where(Source.id == source_id)
    node_query = select(InfraNode).where(InfraNode.source_id.in_(source_query))

    nodes_result = await db.execute(node_query.order_by(InfraNode.kind, InfraNode.name))
    nodes = nodes_result.scalars().all()

    node_ids = {n.id for n in nodes}

    edges_result = await db.execute(select(InfraEdge).where(InfraEdge.from_node_id.in_(node_ids)))
    edges = edges_result.scalars().all()

    manual_edges_query = select(GraphEdgeManual).where(
        GraphEdgeManual.organization_id == ctx.organization_id,
        GraphEdgeManual.project_id == resolved_project_id,
    )
    if source_id:
        manual_edges_query = manual_edges_query.where(GraphEdgeManual.source_id == source_id)
    manual_edges_result = await db.execute(manual_edges_query)
    manual_edges = manual_edges_result.scalars().all()

    notes_query = select(GraphNote).where(
        GraphNote.organization_id == ctx.organization_id,
        GraphNote.project_id == resolved_project_id,
    )
    if source_id:
        notes_query = notes_query.where(GraphNote.source_id == source_id)
    notes_result = await db.execute(notes_query)
    notes = notes_result.scalars().all()

    return {
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "name": n.name,
                "source_id": n.source_id,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "from_node_id": e.from_node_id,
                "to_node_id": e.to_node_id,
                "relation_type": e.relation_type,
            }
            for e in edges
            if e.to_node_id in node_ids
        ],
        "manual_edges": [
            {
                "id": e.id,
                "from_node_id": e.from_node_id,
                "to_node_id": e.to_node_id,
                "label": e.label,
                "color": e.color,
            }
            for e in manual_edges
        ],
        "notes": [
            {
                "id": n.id,
                "content": n.content,
                "color": n.color,
                "pos_x": n.pos_x,
                "pos_y": n.pos_y,
                "from_node_id": n.from_node_id,
                "to_node_id": n.to_node_id,
                "source_id": n.source_id,
            }
            for n in notes
        ],
    }


@router.post("/notes", status_code=201)
async def create_note(
    payload: GraphNoteCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    await require_capability(ctx.organization_id, Capability.GRAPH_ANNOTATIONS, db)
    resolved_project_id, source_id = await _resolve_note_scope(payload, ctx, db)

    note = GraphNote(
        id=uuid.uuid4().hex[:16],
        organization_id=ctx.organization_id,
        project_id=resolved_project_id,
        source_id=source_id,
        from_node_id=payload.from_node_id,
        to_node_id=payload.to_node_id,
        content=payload.content,
        color="#111827",
        pos_x=payload.pos_x,
        pos_y=payload.pos_y,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    if source_id:
        try:
            sync_source.delay(source_id)
        except Exception:
            pass

    return {
        "id": note.id,
        "content": note.content,
        "color": note.color,
        "pos_x": note.pos_x,
        "pos_y": note.pos_y,
        "from_node_id": note.from_node_id,
        "to_node_id": note.to_node_id,
        "source_id": note.source_id,
    }


@router.patch("/notes/{note_id}")
async def update_note(
    note_id: str,
    payload: GraphNoteUpdate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(GraphNote, note_id)
    if not note or note.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.content is not None:
        note.content = payload.content
    if payload.pos_x is not None:
        note.pos_x = payload.pos_x
    if payload.pos_y is not None:
        note.pos_y = payload.pos_y

    await db.commit()
    await db.refresh(note)

    if note.source_id:
        try:
            sync_source.delay(note.source_id)
        except Exception:
            pass
    return {
        "id": note.id,
        "content": note.content,
        "color": note.color,
        "pos_x": note.pos_x,
        "pos_y": note.pos_y,
        "from_node_id": note.from_node_id,
        "to_node_id": note.to_node_id,
        "source_id": note.source_id,
    }


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(GraphNote, note_id)
    if not note or note.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Note not found")
    source_id = note.source_id
    await db.delete(note)
    await db.commit()
    if source_id:
        try:
            sync_source.delay(source_id)
        except Exception:
            pass


@router.post("/edges", status_code=201)
async def create_manual_edge(
    payload: ManualEdgeCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    await require_capability(ctx.organization_id, Capability.MANUAL_GRAPH_EDGES, db)
    from_node = await db.get(InfraNode, payload.from_node_id)
    to_node = await db.get(InfraNode, payload.to_node_id)
    if not from_node or not to_node:
        raise HTTPException(status_code=404, detail="Node not found")

    from_source = await db.get(Source, from_node.source_id)
    to_source = await db.get(Source, to_node.source_id)
    if not from_source or not to_source:
        raise HTTPException(status_code=404, detail="Source not found")
    if (
        from_source.organization_id != ctx.organization_id
        or to_source.organization_id != ctx.organization_id
    ):
        raise HTTPException(status_code=404, detail="Source not found")

    if from_source.project_id != to_source.project_id:
        raise HTTPException(status_code=400, detail="Nodes must be in the same project")

    source_id = from_source.id if from_source.id == to_source.id else None
    project_id = from_source.project_id or await resolve_project_id(None, ctx, db)

    edge = GraphEdgeManual(
        id=uuid.uuid4().hex[:16],
        organization_id=ctx.organization_id,
        project_id=project_id,
        source_id=source_id,
        from_node_id=payload.from_node_id,
        to_node_id=payload.to_node_id,
        label=payload.label,
        color=payload.color or "#f97316",
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)

    try:
        if source_id:
            sync_source.delay(source_id)
        else:
            sync_source.delay(from_source.id)
            sync_source.delay(to_source.id)
    except Exception:
        pass

    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "label": edge.label,
        "color": edge.color,
    }


@router.patch("/edges/{edge_id}")
async def update_manual_edge(
    edge_id: str,
    payload: ManualEdgeUpdate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    edge = await db.get(GraphEdgeManual, edge_id)
    if not edge or edge.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Edge not found")

    if payload.label is not None:
        edge.label = payload.label
    if payload.color is not None:
        edge.color = payload.color

    await db.commit()
    await db.refresh(edge)

    try:
        if edge.source_id:
            sync_source.delay(edge.source_id)
        else:
            from_node = await db.get(InfraNode, edge.from_node_id)
            to_node = await db.get(InfraNode, edge.to_node_id)
            from_source = await db.get(Source, from_node.source_id) if from_node else None
            to_source = await db.get(Source, to_node.source_id) if to_node else None
            if from_source:
                sync_source.delay(from_source.id)
            if to_source and (not from_source or to_source.id != from_source.id):
                sync_source.delay(to_source.id)
    except Exception:
        pass
    return {
        "id": edge.id,
        "from_node_id": edge.from_node_id,
        "to_node_id": edge.to_node_id,
        "label": edge.label,
        "color": edge.color,
    }


@router.delete("/edges/{edge_id}", status_code=204)
async def delete_manual_edge(
    edge_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    edge = await db.get(GraphEdgeManual, edge_id)
    if not edge or edge.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Edge not found")
    source_id = edge.source_id
    from_node_id = edge.from_node_id
    to_node_id = edge.to_node_id
    await db.delete(edge)
    await db.commit()
    try:
        if source_id:
            sync_source.delay(source_id)
        else:
            from_node = await db.get(InfraNode, from_node_id)
            to_node = await db.get(InfraNode, to_node_id)
            from_source = await db.get(Source, from_node.source_id) if from_node else None
            to_source = await db.get(Source, to_node.source_id) if to_node else None
            if from_source:
                sync_source.delay(from_source.id)
            if to_source and (not from_source or to_source.id != from_source.id):
                sync_source.delay(to_source.id)
    except Exception:
        pass
