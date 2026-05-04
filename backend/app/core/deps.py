"""FastAPI dependencies for authentication."""

from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import CurrentContext
from app.core.database import get_db
from app.core.rbac import ensure_membership
from app.core.security import decode_access_token
from app.models.api_key import ApiKey
from app.models.user import User


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Authenticate using either Bearer JWT or API key."""
    auth_header = request.headers.get("Authorization", "")

    if auth_header.startswith("Bearer "):
        return await _authenticate_jwt(auth_header, db)
    elif auth_header.startswith("ApiKey "):
        return await _authenticate_api_key(auth_header, db)
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")


async def get_current_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CurrentContext:
    """Authenticate and resolve the user's org membership."""
    membership = await ensure_membership(db, user.id, create_if_missing=False)
    return CurrentContext(
        user=user,
        organization_id=membership.organization_id,
        role=membership.role,
    )


async def _authenticate_jwt(auth_header: str, db: AsyncSession) -> User:
    """Authenticate using JWT Bearer token."""
    token = auth_header.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _authenticate_api_key(auth_header: str, db: AsyncSession) -> User:
    """Authenticate using API key."""
    key = auth_header.removeprefix("ApiKey ")
    key_hash = ApiKey.hash_key(key)

    result = await db.execute(select(ApiKey).where(ApiKey.key_prefix == key[:16]))
    db_key = result.scalar_one_or_none()

    if not db_key or db_key.key_hash != key_hash:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not db_key.is_valid():
        raise HTTPException(status_code=401, detail="API key expired or revoked")

    # Update last used timestamp
    db_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    # Get the user
    result = await db.execute(select(User).where(User.id == db_key.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    await ensure_membership(db, user.id, create_if_missing=False)
    return user
