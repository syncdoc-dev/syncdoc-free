"""Current user's backend-enforced product capabilities."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.schemas.capabilities import CapabilitiesResponse, CapabilityResponse
from app.services.capabilities import get_capabilities
from app.services.entitlements import get_entitlements

router = APIRouter(tags=["capabilities"])


@router.get("/me/capabilities", response_model=CapabilitiesResponse)
async def read_my_capabilities(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
) -> CapabilitiesResponse:
    entitlements = await get_entitlements(ctx.organization_id, db)
    capabilities = await get_capabilities(ctx.organization_id, db)
    items = [
        CapabilityResponse(
            name=capability.name.value,
            enabled=capability.enabled,
            source=capability.source,
            reason=capability.reason,
            feature=capability.feature,
        )
        for capability in capabilities
    ]
    return CapabilitiesResponse(
        capabilities=items,
        enabled=[item.name for item in items if item.enabled],
        disabled=[item.name for item in items if not item.enabled],
        metadata={
            "plan": entitlements.plan,
            "status": entitlements.status,
            "enforcement_enabled": entitlements.enforcement_enabled,
        },
    )
