"""Offline license verification and entitlement helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import jwt
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.api_key import ApiKey
from app.models.organization_license import OrganizationLicense
from app.models.organization_membership import OrganizationMembership
from app.models.project import Project
from app.models.source import Source

FEATURE_AI_DOCS = "ai_docs"
FEATURE_SEMANTIC_SEARCH = "semantic_search"
FEATURE_ANALYTICS = "analytics"
FEATURE_GRAPH_ANNOTATIONS = "graph_annotations"
FEATURE_MANUAL_GRAPH_EDGES = "manual_graph_edges"

LIMIT_SOURCES = "sources"
LIMIT_USERS = "users"
LIMIT_PROJECTS = "projects"
LIMIT_API_KEYS = "api_keys"

DEFAULT_FREE_LIMITS = {
    LIMIT_SOURCES: 3,
    LIMIT_USERS: 3,
    LIMIT_PROJECTS: 1,
    LIMIT_API_KEYS: 5,
}

PRO_LIMITS = {
    LIMIT_SOURCES: 25,
    LIMIT_USERS: 10,
    LIMIT_PROJECTS: 5,
    LIMIT_API_KEYS: 20,
}

ENTERPRISE_LIMITS = {
    LIMIT_SOURCES: 9999,
    LIMIT_USERS: 9999,
    LIMIT_PROJECTS: 9999,
    LIMIT_API_KEYS: 9999,
}

PLAN_FEATURES: dict[str, set[str]] = {
    "free": set(),
    "pro": {
        FEATURE_AI_DOCS,
        FEATURE_SEMANTIC_SEARCH,
        FEATURE_ANALYTICS,
        FEATURE_GRAPH_ANNOTATIONS,
        FEATURE_MANUAL_GRAPH_EDGES,
    },
    "enterprise": {
        FEATURE_AI_DOCS,
        FEATURE_SEMANTIC_SEARCH,
        FEATURE_ANALYTICS,
        FEATURE_GRAPH_ANNOTATIONS,
        FEATURE_MANUAL_GRAPH_EDGES,
    },
}

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": DEFAULT_FREE_LIMITS,
    "pro": PRO_LIMITS,
    "enterprise": ENTERPRISE_LIMITS,
}


@dataclass(frozen=True)
class Entitlements:
    plan: str
    status: str
    enforcement_enabled: bool
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    features: set[str] = field(default_factory=set)
    limits: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError("Invalid datetime value")


def _base_entitlements(
    *,
    plan: str = "free",
    status: str = "missing",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> Entitlements:
    settings = get_settings()
    features = PLAN_FEATURES.get(plan) or set()
    limits = PLAN_LIMITS.get(plan, DEFAULT_FREE_LIMITS)
    return Entitlements(
        plan=plan,
        status=status,
        enforcement_enabled=settings.license_enforcement_enabled,
        issued_at=issued_at,
        expires_at=expires_at,
        features=set(features),
        limits=dict(limits),
        metadata=metadata or {},
    )


def _decode_unsigned_dev_token(token: str) -> dict[str, Any]:
    payload = json.loads(token)
    if not isinstance(payload, dict):
        raise ValueError("Unsigned license must be a JSON object")
    return payload


def verify_license_token(token: str, organization_id: str) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    payload: dict[str, Any]
    verification_mode = "signed"

    if token.count(".") == 2:
        if not settings.license_public_key:
            raise HTTPException(
                status_code=400,
                detail="LICENSE_PUBLIC_KEY is not configured for signed license verification",
            )
        try:
            payload = jwt.decode(
                token,
                settings.license_public_key,
                algorithms=["RS256", "ES256", "EdDSA"],
                options={"require": ["license_id", "product", "organization_id", "plan"]},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid license token: {exc}") from exc
    else:
        if not settings.license_allow_unsigned_dev:
            raise HTTPException(status_code=400, detail="Unsigned license tokens are not allowed")
        try:
            payload = _decode_unsigned_dev_token(token)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid unsigned license JSON") from exc
        verification_mode = "unsigned_dev"

    if payload.get("product") != "syncdoc":
        raise HTTPException(status_code=400, detail="License product must be 'syncdoc'")
    if payload.get("organization_id") != organization_id:
        raise HTTPException(
            status_code=400,
            detail="License organization does not match current org",
        )
    if payload.get("environment") and payload.get("environment") != "self_hosted":
        raise HTTPException(status_code=400, detail="License environment must be self_hosted")

    return payload, verification_mode


def _entitlements_from_payload(
    payload: dict[str, Any],
    *,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> Entitlements:
    issued_at = _parse_datetime(payload.get("issued_at"))
    expires_at = _parse_datetime(payload.get("expires_at"))
    plan = str(payload.get("plan") or "free")
    plan_features = PLAN_FEATURES.get(plan) or set()
    feature_items = payload.get("features", [])
    if not isinstance(feature_items, list):
        feature_items = []
    features = set(plan_features) | {str(item) for item in feature_items}
    limits = dict(PLAN_LIMITS.get(plan, DEFAULT_FREE_LIMITS))
    payload_limits = payload.get("limits", {})
    if not isinstance(payload_limits, dict):
        payload_limits = {}
    for key, value in payload_limits.items():
        try:
            limits[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return Entitlements(
        plan=plan,
        status=status,
        enforcement_enabled=get_settings().license_enforcement_enabled,
        issued_at=issued_at,
        expires_at=expires_at,
        features=features,
        limits=limits,
        metadata=metadata or {},
    )


async def get_org_license(org_id: str, db: AsyncSession) -> OrganizationLicense | None:
    return await db.get(OrganizationLicense, org_id)


async def get_entitlements(org_id: str, db: AsyncSession) -> Entitlements:
    record = await get_org_license(org_id, db)
    if record is None:
        return _base_entitlements(status="missing")

    try:
        payload, verification_mode = verify_license_token(record.license_token, org_id)
        entitlements = _entitlements_from_payload(
            payload,
            metadata={"verification_mode": verification_mode},
        )
        if entitlements.expires_at and entitlements.expires_at < _now():
            return _base_entitlements(
                status="expired",
                expires_at=entitlements.expires_at,
                metadata={"license_id": payload.get("license_id")},
            )
        return entitlements
    except HTTPException:
        return _base_entitlements(
            status="invalid",
            metadata={"license_id": record.license_id},
        )


def _raise_plan_error(code: str, message: str, entitlements: Entitlements) -> None:
    raise HTTPException(
        status_code=403,
        detail={
            "code": code,
            "message": message,
            "plan": entitlements.plan,
            "status": entitlements.status,
        },
    )


async def assert_feature(org_id: str, feature: str, db: AsyncSession) -> None:
    entitlements = await get_entitlements(org_id, db)
    if not entitlements.enforcement_enabled:
        return
    if feature not in entitlements.features:
        _raise_plan_error(
            "feature_not_in_plan",
            f"{feature.replace('_', ' ').title()} is not available on the current plan.",
            entitlements,
        )


async def assert_limit(org_id: str, limit_name: str, current: int, db: AsyncSession) -> None:
    entitlements = await get_entitlements(org_id, db)
    if not entitlements.enforcement_enabled:
        return
    allowed = entitlements.limits.get(limit_name)
    if allowed is None:
        return
    if current >= allowed:
        _raise_plan_error(
            "plan_limit_exceeded",
            f"{limit_name.replace('_', ' ').title()} limit reached for the current plan.",
            entitlements,
        )


async def count_sources(org_id: str, db: AsyncSession) -> int:
    return int(
        await db.scalar(select(func.count(Source.id)).where(Source.organization_id == org_id)) or 0
    )


async def count_users(org_id: str, db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == org_id
            )
        )
        or 0
    )


async def count_projects(org_id: str, db: AsyncSession) -> int:
    return int(
        await db.scalar(select(func.count(Project.id)).where(Project.organization_id == org_id))
        or 0
    )


async def count_api_keys_for_user(user_id: int, db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count(ApiKey.id)).where(
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None),
            )
        )
        or 0
    )


async def install_license(org_id: str, token: str, db: AsyncSession) -> OrganizationLicense:
    payload, _verification_mode = verify_license_token(token, org_id)
    entitlements = _entitlements_from_payload(payload)
    record = await get_org_license(org_id, db)
    if record is None:
        record = OrganizationLicense(
            organization_id=org_id,
            license_token=token,
        )
        db.add(record)

    record.license_id = str(payload.get("license_id") or "")
    record.plan = entitlements.plan
    record.license_token = token
    record.issued_at = entitlements.issued_at
    record.expires_at = entitlements.expires_at
    record.status = entitlements.status
    record.last_validated_at = _now()
    await db.commit()
    await db.refresh(record)
    return record


async def delete_license(org_id: str, db: AsyncSession) -> None:
    record = await get_org_license(org_id, db)
    if record is None:
        return
    await db.delete(record)
    await db.commit()
