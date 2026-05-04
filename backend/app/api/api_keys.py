"""API Key management endpoints"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.entitlements import LIMIT_API_KEYS, assert_limit, count_api_keys_for_user

router = APIRouter(tags=["api_keys"])


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = 30


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApiKeyWithSecret(BaseModel):
    id: int
    name: str
    key: str
    prefix: str
    created_at: datetime
    expires_at: Optional[datetime]


# Force the path prefix to be /api_keys
@router.post("/api-keys")
async def create_api_key(
    body: ApiKeyCreate,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyWithSecret:
    """Create a new API key for programmatic access."""
    await assert_limit(
        ctx.organization_id,
        LIMIT_API_KEYS,
        await count_api_keys_for_user(ctx.user.id, db),
        db,
    )
    full_key, prefix = ApiKey.generate_key()
    key_hash = ApiKey.hash_key(full_key)

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    db_key = ApiKey(
        user_id=ctx.user.id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        expires_at=expires_at,
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)

    return ApiKeyWithSecret(
        id=db_key.id,
        name=db_key.name,
        key=full_key,
        prefix=db_key.key_prefix,
        created_at=db_key.created_at,
        expires_at=db_key.expires_at,
    )


@router.get("/api-keys")
async def list_api_keys(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current user."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == ctx.user.id)
        .where(ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.key_prefix,
            created_at=k.created_at,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    ctx: CurrentContext = Depends(require_role("member")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == ctx.user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "revoked"}


async def verify_api_key(key: str, db: AsyncSession) -> Optional[User]:
    """Verify an API key and return the user if valid."""
    key_hash = ApiKey.hash_key(key)

    result = await db.execute(select(ApiKey).where(ApiKey.key_prefix == key[:16]))
    db_key = result.scalar_one_or_none()

    if not db_key or db_key.key_hash != key_hash:
        return None

    if not db_key.is_valid():
        return None

    # Update last used timestamp
    db_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # Get the user
    result = await db.execute(select(User).where(User.id == db_key.user_id))
    return result.scalar_one_or_none()
