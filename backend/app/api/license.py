"""Offline license management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.schemas.license import (
    EntitlementsResponse,
    LicenseInstallRequest,
    LicenseRecordResponse,
)
from app.services.entitlements import (
    delete_license,
    get_entitlements,
    get_org_license,
    install_license,
)

router = APIRouter(prefix="/license", tags=["license"])


@router.get("", response_model=LicenseRecordResponse)
async def get_license_record(
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    record = await get_org_license(ctx.organization_id, db)
    settings = get_settings()
    if record is None:
        return LicenseRecordResponse(
            organization_id=ctx.organization_id,
            plan="free",
            status="missing",
            enforcement_enabled=settings.license_enforcement_enabled,
        )
    return LicenseRecordResponse(
        organization_id=record.organization_id,
        license_id=record.license_id,
        plan=record.plan,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        status=record.status,
        last_validated_at=record.last_validated_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        enforcement_enabled=settings.license_enforcement_enabled,
    )


@router.put("", response_model=LicenseRecordResponse)
async def put_license_record(
    payload: LicenseInstallRequest,
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    record = await install_license(ctx.organization_id, payload.license_token, db)
    return LicenseRecordResponse(
        organization_id=record.organization_id,
        license_id=record.license_id,
        plan=record.plan,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        status=record.status,
        last_validated_at=record.last_validated_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        enforcement_enabled=get_settings().license_enforcement_enabled,
    )


@router.delete("", status_code=204)
async def remove_license_record(
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_license(ctx.organization_id, db)


@router.get("/entitlements", response_model=EntitlementsResponse)
async def read_entitlements(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    entitlements = await get_entitlements(ctx.organization_id, db)
    return EntitlementsResponse(
        plan=entitlements.plan,
        status=entitlements.status,
        enforcement_enabled=entitlements.enforcement_enabled,
        issued_at=entitlements.issued_at,
        expires_at=entitlements.expires_at,
        features=sorted(entitlements.features),
        limits=entitlements.limits,
        metadata=entitlements.metadata,
    )
