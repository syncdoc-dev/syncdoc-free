"""Stripe billing API: checkout sessions, webhooks, portal."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import CurrentContext
from app.core.rbac import require_role
from app.models.subscription import Subscription
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
)

router = APIRouter(prefix="/stripe", tags=["stripe"])


def _get_stripe() -> Any:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    req: CheckoutSessionRequest,
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a Stripe Checkout session for subscription."""
    settings = get_settings()
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not enabled")

    s = _get_stripe()

    # Get or create subscription record
    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == ctx.organization_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        sub = Subscription(organization_id=ctx.organization_id)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

    # Get or create Stripe customer
    if not sub.stripe_customer_id:
        try:
            customer = s.Customer.create(
                metadata={"organization_id": ctx.organization_id},
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Stripe customer creation failed: {e.user_message or str(e)}",
            )
        sub.stripe_customer_id = customer.id
        await db.commit()

    # Determine price and trial
    price_id = req.price_id
    is_pro = price_id == settings.stripe_pro_price_id
    is_team = price_id == settings.stripe_team_price_id

    if not is_pro and not is_team:
        raise HTTPException(status_code=400, detail="Invalid price ID")

    # Team plan: enforce minimum 2 seats
    quantity = req.quantity or 1
    if is_team and quantity < 2:
        raise HTTPException(status_code=400, detail="Team plan requires at least 2 seats")

    session_params: dict[str, Any] = {
        "customer": sub.stripe_customer_id,
        "client_reference_id": ctx.organization_id,
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": [
            {
                "price": price_id,
                "quantity": quantity,
            }
        ],
        "success_url": (
            f"{settings.frontend_url.rstrip('/')}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        ),
        "cancel_url": f"{settings.frontend_url.rstrip('/')}/billing/canceled",
        "subscription_data": {
            "metadata": {"organization_id": ctx.organization_id},
        },
    }

    # Add trial only for Pro plan
    if is_pro and settings.stripe_trial_days > 0:
        session_params["subscription_data"]["trial_period_days"] = settings.stripe_trial_days

    try:
        checkout_session = s.checkout.Session.create(**session_params)
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe checkout failed: {e.user_message or str(e)}",
        )

    return {"checkout_url": checkout_session.url}


@router.post("/portal-session")
async def create_portal_session(
    ctx: CurrentContext = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a Stripe Billing Portal session."""
    settings = get_settings()
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not enabled")

    s = _get_stripe()

    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == ctx.organization_id)
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active Stripe customer")

    try:
        portal_session = s.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.frontend_url.rstrip('/')}/settings/billing",
        )
    except stripe.error.InvalidRequestError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {e.user_message or str(e)}")
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe service error: {e.user_message or str(e)}",
        )

    return {"portal_url": portal_session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Handle Stripe webhooks."""
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    await _handle_stripe_event(event, db)
    return {"status": "ok"}


async def _handle_stripe_event(event: Any, db: AsyncSession) -> None:
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.created":
        await _handle_subscription_updated(data, db)
    elif event_type == "invoice.payment_succeeded":
        await _handle_invoice_paid(data, db)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)


async def _handle_checkout_completed(data: Any, db: AsyncSession) -> None:
    org_id = data.client_reference_id or (
        data.subscription_data.metadata.organization_id
        if hasattr(data, "subscription_data")
        and hasattr(data.subscription_data, "metadata")
        else None
    )
    if not org_id:
        return

    result = await db.execute(select(Subscription).where(Subscription.organization_id == org_id))
    sub = result.scalar_one_or_none()
    if not sub:
        sub = Subscription(organization_id=org_id)
        db.add(sub)

    sub.stripe_customer_id = data.customer
    if hasattr(data, "subscription") and data.subscription:
        sub.stripe_subscription_id = data.subscription
    # User has paid — mark as active immediately
    sub.status = "active"
    await db.commit()


async def _handle_invoice_paid(data: Any, db: AsyncSession) -> None:
    subscription_id = data.subscription if hasattr(data, "subscription") else None
    if not subscription_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = "active"
    await db.commit()


async def _handle_subscription_updated(data: Any, db: AsyncSession) -> None:
    subscription_id = data.id if hasattr(data, "id") else None
    if not subscription_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = data.status if hasattr(data, "status") else sub.status
    sub.current_period_end = _timestamp_to_datetime(
        data.current_period_end if hasattr(data, "current_period_end") else None
    )
    sub.trial_end = _timestamp_to_datetime(
        data.trial_end if hasattr(data, "trial_end") else None
    )

    # Update price/plan if changed
    if hasattr(data, "items") and hasattr(data.items, "data") and data.items.data:
        item = data.items.data[0]
        if hasattr(item, "price") and hasattr(item.price, "id"):
            sub.stripe_price_id = item.price.id
        if hasattr(item, "quantity"):
            sub.seat_count = item.quantity

    await db.commit()


async def _handle_subscription_deleted(data: Any, db: AsyncSession) -> None:
    subscription_id = data.id if hasattr(data, "id") else None
    if not subscription_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.status = "canceled"
    sub.stripe_subscription_id = None
    await db.commit()


def _timestamp_to_datetime(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@router.get("/billing/status", response_model=BillingStatusResponse)
async def billing_status(
    ctx: CurrentContext = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current billing status for the organization."""
    settings = get_settings()
    if not settings.billing_enabled:
        return {
            "billing_enabled": False,
            "plan": "open_source",
            "status": "active",
            "trial_days_remaining": None,
            "current_period_end": None,
            "seat_count": 1,
            "checkout_required": False,
        }

    result = await db.execute(
        select(Subscription).where(Subscription.organization_id == ctx.organization_id)
    )
    sub = result.scalar_one_or_none()

    if sub is None:
        # No subscription record yet — brand new org, needs checkout
        return {
            "billing_enabled": True,
            "plan": "free",
            "status": "trialing",
            "trial_days_remaining": settings.stripe_trial_days,
            "current_period_end": None,
            "seat_count": 1,
            "checkout_required": True,
        }

    trial_days = None
    if sub.status == "trialing":
        if sub.trial_end:
            delta = sub.trial_end - datetime.now(timezone.utc)
            trial_days = max(0, delta.days)
        else:
            # Legacy subscription without trial_end — grant full trial period
            trial_days = settings.stripe_trial_days

    # Owner plan is permanent — but only for the designated owner login
    is_authorized_owner = (
        sub.plan == "owner"
        and settings.owner_login
        and ctx.login == settings.owner_login
    )
    if is_authorized_owner:
        checkout_required = False
    else:
        checkout_required = (
            sub.status in ("trialing", "unpaid", "past_due") and not sub.stripe_subscription_id
        )

    # Mask unauthorized owner plans as pro
    plan = sub.plan if is_authorized_owner else "pro" if sub.plan == "owner" else sub.plan

    return {
        "billing_enabled": True,
        "plan": plan,
        "status": sub.status,
        "trial_days_remaining": trial_days,
        "current_period_end": sub.current_period_end,
        "seat_count": sub.seat_count,
        "checkout_required": checkout_required,
        "stripe_subscription_id": sub.stripe_subscription_id,
    }
