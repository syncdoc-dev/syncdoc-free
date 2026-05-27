"""Billing gate dependency."""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.models.subscription import Subscription


async def require_paid_org(
    ctx: CurrentContext = Depends(),
    db: AsyncSession = Depends(get_db),
) -> CurrentContext:
    """Dependency that raises 402 if the org has no active subscription or expired trial."""
    settings = get_settings()
    if not settings.billing_enabled:
        return ctx

    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == ctx.organization_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        # No subscription at all — first time, allow trialing
        sub = Subscription(
            organization_id=ctx.organization_id,
            status="trialing",
            trial_end=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        )
        # Don't persist here; let the checkout flow handle it
        raise HTTPException(
            status_code=402,
            detail={
                "code": "payment_required",
                "message": "Subscription required to continue.",
                "trial_days_remaining": settings.stripe_trial_days,
                "checkout_required": True,
            },
        )

    if sub.status in ("active", "trialing") or sub.plan == "owner":
        # Owner plan bypasses all billing checks — but only for the designated owner login
        if sub.plan == "owner":
            if settings.owner_login and ctx.login == settings.owner_login:
                return ctx
            # Unauthorized owner plan — treat as needing payment
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "payment_required",
                    "message": "Subscription required to continue.",
                    "trial_days_remaining": settings.stripe_trial_days,
                    "checkout_required": True,
                },
            )
        # Check if trial has expired
        if (
            sub.status == "trialing"
            and sub.trial_end
            and sub.trial_end <= datetime.now(timezone.utc)
        ):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "trial_expired",
                    "message": "Your trial has expired. Please subscribe to continue.",
                    "trial_days_remaining": 0,
                    "checkout_required": True,
                },
            )
        return ctx

    if sub.status in ("canceled", "unpaid", "past_due"):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "subscription_inactive",
                "message": "Your subscription is inactive. Please renew to continue.",
                "checkout_required": True,
            },
        )

    return ctx
