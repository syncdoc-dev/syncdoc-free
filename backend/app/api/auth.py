"""Authentication endpoints: GitHub OAuth and local username/password."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import jwt as pyjwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import create_personal_org_membership, ensure_membership
from app.core.security import (
    create_access_token,
    decode_access_token,
    encrypt_token,
    hash_password,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email import (
    EmailConfigurationError,
    safe_send_registration_emails,
    send_password_reset_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ALLOWED_THEMES = {
    "original",
    "original_light",
    "catppuccin",
    "tokyonight",
    "dracula",
    "nord",
    "gruvbox",
}


def _raise_if_db_not_ready(err: Exception) -> None:
    if isinstance(err, ProgrammingError) and "UndefinedTableError" in str(err.orig):
        raise HTTPException(
            status_code=503,
            detail="Database not migrated yet. Please retry in a few minutes.",
        ) from err


# Schemas
class LoginRequest(BaseModel):
    """Local login request."""

    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)


class RegisterRequest(BaseModel):
    """Local registration request."""

    login: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    name: str | None = Field(None, max_length=100)
    marketing_opt_in: bool = False
    bootstrap_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    login_or_email: str = Field(..., min_length=3, max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    password: str = Field(..., min_length=8, max_length=72)


class AuthResponse(BaseModel):
    """Authentication response with JWT token."""

    access_token: str
    token_type: str = "bearer"
    user: dict[str, object]


class UpdateMeRequest(BaseModel):
    theme_id: str | None = None


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register", response_model=AuthResponse)
async def register(
    req: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new local user."""
    settings = get_settings()
    if not settings.allow_self_register:
        token = req.bootstrap_token or request.headers.get("X-Bootstrap-Token")
        if (
            not token
            or not settings.bootstrap_token
            or not secrets.compare_digest(token, settings.bootstrap_token)
        ):
            raise HTTPException(status_code=403, detail="Registration disabled")
    # Check if user exists
    try:
        result = await db.execute(select(User).where(User.login == req.login))
    except Exception as e:
        _raise_if_db_not_ready(e)
        raise
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    try:
        result = await db.execute(select(User).where(User.email == req.email))
    except Exception as e:
        _raise_if_db_not_ready(e)
        raise
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Create user
    user = User(
        login=req.login,
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        auth_provider="local",
        marketing_opt_in=req.marketing_opt_in,
        marketing_opt_in_at=datetime.now(timezone.utc) if req.marketing_opt_in else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(safe_send_registration_emails, user, source="local_register")

    membership = await create_personal_org_membership(db, user.id, org_name=f"{user.login}'s Org")

    # Issue JWT
    jwt_token = create_access_token(
        {
            "sub": str(user.id),
            "login": user.login,
            "org_id": membership.organization_id,
            "role": membership.role,
        }
    )

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "name": user.name,
            "theme_id": user.theme_id,
            "marketing_opt_in": user.marketing_opt_in,
            "organization_id": membership.organization_id,
            "role": membership.role,
        },
    }


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """Login with username and password."""
    try:
        result = await db.execute(
            select(User).where(or_(User.login == req.login, User.email == req.login))
        )
    except Exception as e:
        _raise_if_db_not_ready(e)
        raise
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        membership = await ensure_membership(db, user.id, create_if_missing=False)
    except HTTPException:
        membership = await create_personal_org_membership(
            db, user.id, org_name=f"{user.login}'s Org"
        )

    # Issue JWT
    jwt_token = create_access_token(
        {
            "sub": str(user.id),
            "login": user.login,
            "org_id": membership.organization_id,
            "role": membership.role,
        }
    )

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "name": user.name,
            "theme_id": user.theme_id,
            "organization_id": membership.organization_id,
            "role": membership.role,
        },
    }


@router.get("/github")
async def github_login() -> RedirectResponse:
    settings = get_settings()
    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        "&scope=repo,read:user,user:email"
        f"&redirect_uri={settings.backend_url.rstrip('/')}/api/auth/github/callback"
    )
    return RedirectResponse(github_auth_url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token: str | None = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    # Fetch GitHub user info
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        github_user = user_resp.json()

        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        emails = email_resp.json()

    primary_email: str | None = next(
        (e["email"] for e in emails if isinstance(e, dict) and e.get("primary")),
        None,
    )

    # Upsert user
    try:
        result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    except Exception as e:
        _raise_if_db_not_ready(e)
        raise
    user = result.scalar_one_or_none()
    is_new_user = user is None

    encrypted_token = encrypt_token(access_token)

    if user is None:
        if not settings.allow_self_register:
            raise HTTPException(status_code=403, detail="Registration disabled")
        user = User(
            github_id=github_user["id"],
            login=github_user["login"],
            email=primary_email,
            name=github_user.get("name"),
            avatar_url=github_user.get("avatar_url"),
            github_access_token=encrypted_token,
            auth_provider="github",
            marketing_opt_in=False,
        )
        db.add(user)
    else:
        user.github_access_token = encrypted_token
        user.name = github_user.get("name")
        user.avatar_url = github_user.get("avatar_url")
        if primary_email:
            user.email = primary_email

    await db.commit()
    await db.refresh(user)

    if is_new_user:
        background_tasks.add_task(safe_send_registration_emails, user, source="github_oauth")

    try:
        membership = await ensure_membership(db, user.id, create_if_missing=False)
    except HTTPException:
        membership = await create_personal_org_membership(
            db, user.id, org_name=f"{user.login}'s Org"
        )

    # Issue JWT
    jwt_token = create_access_token(
        {
            "sub": str(user.id),
            "login": user.login,
            "org_id": membership.organization_id,
            "role": membership.role,
        }
    )

    # Redirect to frontend callback so token is stored before protected routes render
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback?token={jwt_token}")


@router.get("/me")
async def get_me(request: Request, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

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
        raise HTTPException(status_code=404, detail="User not found")

    try:
        membership = await ensure_membership(db, user.id, create_if_missing=False)
    except HTTPException:
        membership = await create_personal_org_membership(
            db, user.id, org_name=f"{user.login}'s Org"
        )

    return {
        "id": user.id,
        "login": user.login,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "theme_id": user.theme_id,
        "marketing_opt_in": user.marketing_opt_in,
        "organization_id": membership.organization_id,
        "role": membership.role,
    }


@router.patch("/me")
async def update_me(
    payload: UpdateMeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.removeprefix("Bearer ")
    try:
        payload_token = decode_access_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload_token["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.theme_id is not None:
        if payload.theme_id not in ALLOWED_THEMES:
            raise HTTPException(status_code=400, detail="Invalid theme")
        user.theme_id = payload.theme_id

    await db.commit()
    await db.refresh(user)

    try:
        membership = await ensure_membership(db, user.id, create_if_missing=False)
    except HTTPException:
        membership = await create_personal_org_membership(
            db, user.id, org_name=f"{user.login}'s Org"
        )

    return {
        "id": user.id,
        "login": user.login,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "theme_id": user.theme_id,
        "marketing_opt_in": user.marketing_opt_in,
        "organization_id": membership.organization_id,
        "role": membership.role,
    }


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    settings = get_settings()
    if not settings.email_enabled:
        raise HTTPException(status_code=503, detail="Email delivery is not configured")

    try:
        result = await db.execute(
            select(User).where(
                or_(User.login == req.login_or_email, User.email == req.login_or_email)
            )
        )
    except Exception as e:
        _raise_if_db_not_ready(e)
        raise
    user = result.scalar_one_or_none()

    if user and user.email:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                id=str(uuid4()),
                user_id=user.id,
                token_hash=_hash_reset_token(raw_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.password_reset_expire_minutes),
            )
        )
        await db.commit()

        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw_token}"
        try:
            await send_password_reset_email(user, reset_url)
        except EmailConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"detail": "If an account exists for that login or email, a reset email has been sent."}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash_reset_token(req.token)
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if token_record.used_at or token_record.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(req.password)
    token_record.used_at = datetime.now(timezone.utc)
    await db.commit()

    return {"detail": "Password reset successfully"}
