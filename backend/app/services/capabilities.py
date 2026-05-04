"""Backend-enforced product capability checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.entitlements import (
    FEATURE_AI_DOCS,
    FEATURE_ANALYTICS,
    FEATURE_GRAPH_ANNOTATIONS,
    FEATURE_MANUAL_GRAPH_EDGES,
    FEATURE_SEMANTIC_SEARCH,
    Entitlements,
    get_entitlements,
)


class Capability(StrEnum):
    AI_GENERATION = "ai_generation"
    SEMANTIC_SEARCH = "semantic_search"
    ANALYTICS = "analytics"
    GRAPH_ANNOTATIONS = "graph_annotations"
    MANUAL_GRAPH_EDGES = "manual_graph_edges"
    SCHEDULED_SYNC = "scheduled_sync"
    TEAM_WORKSPACES = "team_workspaces"
    AUDIT_LOGS = "audit_logs"
    SSO = "sso"
    ADVANCED_EXPORTS = "advanced_exports"


@dataclass(frozen=True)
class CapabilityState:
    name: Capability
    enabled: bool
    source: str
    reason: str | None = None
    feature: str | None = None


CAPABILITY_FEATURES: dict[Capability, str] = {
    Capability.AI_GENERATION: FEATURE_AI_DOCS,
    Capability.SEMANTIC_SEARCH: FEATURE_SEMANTIC_SEARCH,
    Capability.ANALYTICS: FEATURE_ANALYTICS,
    Capability.GRAPH_ANNOTATIONS: FEATURE_GRAPH_ANNOTATIONS,
    Capability.MANUAL_GRAPH_EDGES: FEATURE_MANUAL_GRAPH_EDGES,
}

HOSTED_SAAS_CAPABILITIES: set[Capability] = {
    Capability.SCHEDULED_SYNC,
    Capability.TEAM_WORKSPACES,
    Capability.AUDIT_LOGS,
    Capability.SSO,
    Capability.ADVANCED_EXPORTS,
}


def resolve_capability(
    capability: Capability,
    entitlements: Entitlements,
) -> CapabilityState:
    feature = CAPABILITY_FEATURES.get(capability)
    if feature is not None:
        enabled = (not entitlements.enforcement_enabled) or feature in entitlements.features
        reason = None if enabled else "feature_not_in_plan"
        return CapabilityState(
            name=capability,
            enabled=enabled,
            source="license",
            reason=reason,
            feature=feature,
        )

    if capability in HOSTED_SAAS_CAPABILITIES:
        return CapabilityState(
            name=capability,
            enabled=False,
            source="hosted_saas",
            reason="hosted_saas_only",
        )

    return CapabilityState(
        name=capability,
        enabled=True,
        source="core",
    )


def resolve_capabilities(entitlements: Entitlements) -> list[CapabilityState]:
    return [resolve_capability(capability, entitlements) for capability in Capability]


async def get_capabilities(org_id: str, db: AsyncSession) -> list[CapabilityState]:
    entitlements = await get_entitlements(org_id, db)
    return resolve_capabilities(entitlements)


async def is_capability_enabled(org_id: str, capability: Capability, db: AsyncSession) -> bool:
    entitlements = await get_entitlements(org_id, db)
    return resolve_capability(capability, entitlements).enabled


async def require_capability(org_id: str, capability: Capability, db: AsyncSession) -> None:
    entitlements = await get_entitlements(org_id, db)
    state = resolve_capability(capability, entitlements)
    if state.enabled:
        return

    raise HTTPException(
        status_code=403,
        detail={
            "code": state.reason or "capability_unavailable",
            "message": f"{capability.value.replace('_', ' ').title()} is not available.",
            "capability": capability.value,
            "feature": state.feature,
            "plan": entitlements.plan,
            "status": entitlements.status,
        },
    )
