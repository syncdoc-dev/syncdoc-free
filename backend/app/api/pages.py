"""Pages API endpoints"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.models.page import DocPage
from app.models.source import Source
from app.models.workflow import PageWorkflow
from app.schemas.page import PageCreate, PageResponse, PageUpdate
from app.schemas.workflow import WorkflowStateResponse
from app.services.capabilities import Capability, require_capability
from app.services.doc_generator import generate_doc_for_source

router = APIRouter()


@router.get("/", response_model=List[PageResponse])
async def list_pages(
    source_id: Optional[str] = None,
    include_workflow: bool = False,
    project_id: str | None = None,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """List all wiki pages, optionally filtered by source_id"""
    resolved_project_id = await resolve_project_id(project_id, ctx, db)
    query = select(DocPage).where(
        DocPage.organization_id == ctx.organization_id,
        DocPage.project_id == resolved_project_id,
    )
    if source_id:
        source = await db.get(Source, source_id)
        if not source or source.organization_id != ctx.organization_id:
            raise HTTPException(status_code=404, detail="Source not found")
        query = query.where(DocPage.source_id == source_id)
    query = query.order_by(DocPage.updated_at.desc())
    result = await db.execute(query)
    pages = result.scalars().all()

    if include_workflow and pages:
        page_ids = [p.id for p in pages]
        workflow_result = await db.execute(
            select(PageWorkflow).where(PageWorkflow.page_id.in_(page_ids))
        )
        workflows = {w.page_id: w for w in workflow_result.scalars().all()}

        response_pages = []
        for page in pages:
            page_dict = {
                "id": page.id,
                "source_id": page.source_id,
                "project_id": page.project_id,
                "title": page.title,
                "content_md": page.content_md,
                "version": page.version,
                "is_manually_edited": page.is_manually_edited,
                "created_at": page.created_at,
                "updated_at": page.updated_at,
                "workflow": (
                    WorkflowStateResponse.model_validate(workflows[page.id]).model_dump()
                    if page.id in workflows
                    else None
                ),
            }
            response_pages.append(page_dict)
        return response_pages

    return pages


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific page"""
    page = await db.get(DocPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/", response_model=PageResponse, status_code=201)
async def create_page(
    page: PageCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new wiki page (manual)"""
    resolved_project_id = await resolve_project_id(page.project_id, ctx, db)
    if page.source_id:
        source = await db.get(Source, page.source_id)
        if not source or source.organization_id != ctx.organization_id:
            raise HTTPException(status_code=404, detail="Source not found")
        resolved_project_id = source.project_id or resolved_project_id
    db_page = DocPage(
        id=uuid.uuid4().hex[:16],
        title=page.title,
        content_md=page.content_md,
        source_id=page.source_id,
        is_manually_edited=1,
        organization_id=ctx.organization_id,
        project_id=resolved_project_id,
    )
    db.add(db_page)
    await db.commit()
    await db.refresh(db_page)
    return db_page


@router.put("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: str,
    page: PageUpdate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Update a wiki page (marks as manually edited)"""
    db_page = await db.get(DocPage, page_id)
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")
    if db_page.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Page not found")

    if page.title is not None:
        db_page.title = page.title  # type: ignore[assignment]
    if page.content_md is not None:
        db_page.content_md = page.content_md  # type: ignore[assignment]
    db_page.is_manually_edited = 1  # type: ignore[assignment]
    db_page.version += 1  # type: ignore[assignment]

    await db.commit()
    await db.refresh(db_page)
    return db_page


@router.post("/{page_id}/regenerate", response_model=PageResponse)
async def regenerate_page(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate a page from its source, even if manually edited."""
    await require_capability(ctx.organization_id, Capability.AI_GENERATION, db)
    page = await db.get(DocPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Page not found")
    if not page.source_id:
        raise HTTPException(status_code=400, detail="Page has no source")

    regenerated = await generate_doc_for_source(page.source_id, db, force=True)
    if not regenerated:
        raise HTTPException(status_code=400, detail="Unable to regenerate page")
    return regenerated


@router.delete("/{page_id}", status_code=204)
async def delete_page(
    page_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a page"""
    page = await db.get(DocPage, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Page not found")
    await db.delete(page)
    await db.commit()
