"""Projects API endpoints"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.entitlements import LIMIT_PROJECTS, assert_limit, count_projects

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .where(Project.organization_id == ctx.organization_id)
        .order_by(Project.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_limit(
        ctx.organization_id,
        LIMIT_PROJECTS,
        await count_projects(ctx.organization_id, db),
        db,
    )
    existing = await db.execute(
        select(Project).where(
            Project.organization_id == ctx.organization_id, Project.name == payload.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project name already exists")

    project = Project(
        id=str(uuid.uuid4()),
        organization_id=ctx.organization_id,
        name=payload.name,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project
