"""Billing and Stripe schemas."""

from datetime import datetime

from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    price_id: str
    quantity: int = 1


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingStatusResponse(BaseModel):
    billing_enabled: bool
    plan: str
    status: str
    trial_days_remaining: int | None
    current_period_end: datetime | None
    seat_count: int
    checkout_required: bool
    stripe_subscription_id: str | None = None
