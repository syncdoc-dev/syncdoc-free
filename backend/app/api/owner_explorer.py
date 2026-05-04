"""Owner-only curated data explorer endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role, resolve_project_id
from app.schemas.owner_explorer import (
    OwnerExplorerDetailResponse,
    OwnerExplorerListResponse,
    OwnerExplorerResource,
)
from app.services.owner_explorer import get_resource_item, list_resource_items, list_resources

router = APIRouter(prefix="/owner-explorer", tags=["owner_explorer"])


@router.get("/resources", response_model=list[OwnerExplorerResource])
async def get_resources(
    ctx: CurrentContext = Depends(require_role("owner")),
):
    return list_resources()


@router.get("/{resource}", response_model=OwnerExplorerListResponse)
async def get_resource_items(
    resource: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    project_id: str | None = Query(None),
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    resolved_project_id = None
    if project_id:
        resolved_project_id = await resolve_project_id(project_id, ctx, db)
    return await list_resource_items(
        db,
        ctx=ctx,
        resource=resource,
        limit=limit,
        offset=offset,
        q=q,
        project_id=resolved_project_id,
    )


@router.get("/{resource}/{item_id}", response_model=OwnerExplorerDetailResponse)
async def get_resource_detail(
    resource: str,
    item_id: str,
    project_id: str | None = Query(None),
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    resolved_project_id = None
    if project_id:
        resolved_project_id = await resolve_project_id(project_id, ctx, db)
    return await get_resource_item(
        db,
        ctx=ctx,
        resource=resource,
        item_id=item_id,
        project_id=resolved_project_id,
    )
