"""Credentials API endpoints for managing source authentication."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.source import Source
from app.schemas.credential import CredentialCreate, CredentialListResponse, CredentialResponse
from app.services.credentials import CredentialManager

router = APIRouter(prefix="/sources", tags=["credentials"])


@router.post("/{source_id}/credentials", response_model=CredentialResponse, status_code=201)
async def create_credential(
    source_id: str,
    cred: CredentialCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new credential for a source."""
    # Verify source exists
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    # Create credential (no user_id for now, can be added with auth)
    created_cred = await CredentialManager.store_credential(
        db,
        source_id=source_id,
        credential_type=cred.credential_type,
        secret_value=cred.secret_value,
        created_by=None,
    )
    await db.commit()
    await db.refresh(created_cred)
    return created_cred


@router.get("/{source_id}/credentials", response_model=CredentialListResponse)
async def list_credentials(
    source_id: str,
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
):
    """List all credentials for a source (without secret values)."""
    # Verify source exists
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    credentials = await CredentialManager.get_all_credentials(db, source_id)
    return CredentialListResponse(
        source_id=source_id,
        credentials=[CredentialResponse.model_validate(c) for c in credentials],
    )


@router.delete("/{source_id}/credentials/{credential_id}", status_code=204)
async def delete_credential(
    source_id: str,
    credential_id: str,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a credential."""
    # Verify source exists
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Source not found")

    deleted = await CredentialManager.delete_credential(db, credential_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")

    await db.commit()
