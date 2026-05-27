"""RBAC helpers for organization and project scoping."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.context import CurrentContext
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.project import Project
from app.models.user import User

ROLE_ORDER = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}


def require_role(min_role: str):
    from app.core.deps import get_current_context

    async def _require(ctx: CurrentContext = Depends(get_current_context)) -> CurrentContext:
        if ROLE_ORDER.get(ctx.role, 0) < ROLE_ORDER.get(min_role, 0):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return ctx

    return _require


async def resolve_project_id(
    project_id: str | None,
    ctx: CurrentContext,
    db: AsyncSession,
) -> str:
    if project_id:
        result = await db.execute(
            select(Project).where(
                Project.id == project_id, Project.organization_id == ctx.organization_id
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.id

    result = await db.execute(
        select(Project)
        .where(Project.organization_id == ctx.organization_id)
        .order_by(Project.created_at.asc())
        .limit(1)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=400, detail="No projects available")
    return project.id


async def ensure_membership(
    db: AsyncSession,
    user_id: int,
    *,
    create_if_missing: bool = True,
) -> OrganizationMembership:
    result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if membership:
        return membership

    if not create_if_missing:
        raise HTTPException(status_code=403, detail="No organization membership")

    # Serialize first-time org/membership creation to avoid race conditions.
    await db.execute(text("SELECT pg_advisory_xact_lock(:lock_key)").bindparams(lock_key=1))

    # Re-check after acquiring the lock.
    result = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if membership:
        return membership

    # Determine role for new member
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    settings = get_settings()

    is_owner = settings.owner_login and user.login == settings.owner_login

    if settings.owner_login and not is_owner:
        # Hosted mode, non-owner user: always create their own isolated org
        org = Organization(id=str(uuid.uuid4()), name=f"{user.login}'s Org")
        db.add(org)
        await db.flush()
        role = "owner"  # They are the owner of their own org
    else:
        # Self-hosted mode OR designated owner: use the first/default org
        org_result = await db.execute(select(Organization).limit(1))
        org = org_result.scalar_one_or_none()
        if org is None:
            org = Organization(id=str(uuid.uuid4()), name="Default")
            db.add(org)
            await db.flush()
        role = "owner" if is_owner else "admin"

    project_result = await db.execute(
        select(Project).where(Project.organization_id == org.id).limit(1)
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        project = Project(id=str(uuid.uuid4()), organization_id=org.id, name="General")
        db.add(project)
        await db.flush()

    membership = OrganizationMembership(user_id=user_id, organization_id=org.id, role=role)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership
