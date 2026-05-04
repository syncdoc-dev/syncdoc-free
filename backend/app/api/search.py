"""Search API: full-text + semantic search across infrastructure nodes and documentation pages."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.node import InfraNode
from app.models.page import DocPage
from app.models.source import Source
from app.services.capabilities import Capability, is_capability_enabled
from app.services.embeddings import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    project_id: str | None = None,
    ctx: CurrentContext = Depends(require_role("viewer")),
    session: AsyncSession = Depends(get_db),
):
    """Search infrastructure nodes and documentation pages by keyword or semantic similarity."""
    term = f"%{q}%"
    resolved_project_id = await resolve_project_id(project_id, ctx, session)
    semantic_allowed = await is_capability_enabled(
        ctx.organization_id,
        Capability.SEMANTIC_SEARCH,
        session,
    )
    source_query = select(Source.id).where(
        Source.organization_id == ctx.organization_id, Source.project_id == resolved_project_id
    )

    # Search nodes by name, kind, or config
    node_query = (
        select(InfraNode)
        .where(
            or_(
                InfraNode.name.ilike(term),
                InfraNode.kind.ilike(term),
            )
        )
        .where(InfraNode.source_id.in_(source_query))
        .limit(limit)
    )
    node_results = (await session.execute(node_query)).scalars().all()

    # Try semantic search first
    search_mode = "keyword"
    embedding = None

    if semantic_allowed:
        try:
            embedding = await get_embedding(q)
            if embedding:
                has_embeddings = await session.scalar(
                    select(func.count(DocPage.id)).where(
                        DocPage.embedding.isnot(None),
                        DocPage.organization_id == ctx.organization_id,
                        DocPage.project_id == resolved_project_id,
                    )
                )
                if (has_embeddings or 0) > 0:
                    search_mode = "semantic"
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")

    # Search pages
    if search_mode == "semantic" and embedding:
        # Vector similarity search using cosine distance (op "<->" for pgvector)
        page_query = (
            select(DocPage)
            .where(
                DocPage.organization_id == ctx.organization_id,
                DocPage.project_id == resolved_project_id,
            )
            .order_by(DocPage.embedding.op("<->")(embedding))
            .limit(limit)
        )
    else:
        # Fallback to keyword search
        page_query = (
            select(DocPage)
            .where(
                or_(
                    DocPage.title.ilike(term),
                    DocPage.content_md.ilike(term),
                )
            )
            .where(
                DocPage.organization_id == ctx.organization_id,
                DocPage.project_id == resolved_project_id,
            )
            .limit(limit)
        )
    page_results = (await session.execute(page_query)).scalars().all()

    return {
        "query": q,
        "search_mode": search_mode,
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "name": n.name,
                "source_id": n.source_id,
                "match_type": "node",
            }
            for n in node_results
        ],
        "pages": [
            {
                "id": p.id,
                "title": p.title,
                "source_id": p.source_id,
                "snippet": _snippet(p.content_md, q),
                "match_type": "page",
            }
            for p in page_results
        ],
    }


def _snippet(text: str, query: str, context: int = 120) -> str:
    """Extract a snippet around the first occurrence of the query term."""
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:context] + ("..." if len(text) > context else "")
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(query) + context // 2)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
