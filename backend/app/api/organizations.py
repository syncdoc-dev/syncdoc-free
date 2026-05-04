"""Organization API endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.core.security import hash_password
from app.models.api_key import ApiKey
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationUpdate,
    OrgMemberResponse,
    OrgMemberRoleUpdate,
    OrgUserCreate,
)
from app.services.entitlements import LIMIT_USERS, assert_limit, count_users

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("/me", response_model=OrganizationResponse)
async def get_org(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/me", response_model=OrganizationResponse)
async def update_org(
    payload: OrganizationUpdate,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, ctx.organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.name = payload.name
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/members", response_model=list[OrgMemberResponse])
async def list_members(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == ctx.organization_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    rows = result.all()
    can_view_emails = ctx.role in {"owner", "admin"}
    return [
        OrgMemberResponse(
            user_id=user.id,
            login=user.login,
            email=user.email if can_view_emails else None,
            role=membership.role,
            created_at=membership.created_at,
        )
        for membership, user in rows
    ]


@router.post("/users", response_model=OrgMemberResponse, status_code=201)
async def create_user(
    payload: OrgUserCreate,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    await assert_limit(
        ctx.organization_id,
        LIMIT_USERS,
        await count_users(ctx.organization_id, db),
        db,
    )
    existing = await db.execute(select(User).where(User.login == payload.login))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Login already exists")
    if payload.email:
        existing_email = await db.execute(select(User).where(User.email == payload.email))
        if existing_email.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already exists or email is in use")

    if ctx.role != "owner" and payload.role in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Only owners can assign admin/owner role")

    user = User(
        login=payload.login,
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        auth_provider="local",
    )
    db.add(user)
    await db.flush()

    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=ctx.organization_id,
        role=payload.role,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    return OrgMemberResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.patch("/members/{user_id}", response_model=OrgMemberResponse)
async def update_member_role(
    user_id: int,
    payload: OrgMemberRoleUpdate,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == ctx.organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    membership, user = row
    if ctx.role != "owner" and payload.role in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Only owners can assign admin/owner role")

    if membership.role == "owner" and payload.role != "owner":
        owner_count = await db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == ctx.organization_id,
                OrganizationMembership.role == "owner",
            )
        )
        if owner_count == 1:
            raise HTTPException(status_code=403, detail="Cannot remove the last owner")

    membership.role = payload.role
    await db.commit()
    await db.refresh(membership)
    return OrgMemberResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    ctx: CurrentContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == ctx.organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    membership, user = row

    if ctx.role != "owner" and membership.role in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Only owners can delete admin/owner users")

    if membership.role == "owner":
        owner_count = await db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == ctx.organization_id,
                OrganizationMembership.role == "owner",
            )
        )
        if owner_count == 1:
            raise HTTPException(status_code=403, detail="Cannot delete the last owner")

    await db.execute(delete(ApiKey).where(ApiKey.user_id == user.id))
    await db.delete(user)
    await db.commit()
