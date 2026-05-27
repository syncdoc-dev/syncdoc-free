"""Stripe subscription model for SaaS billing."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Subscription(Base):
    """Stripe subscription tied to an organization."""

    __tablename__ = "subscriptions"

    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String, nullable=True, unique=True, index=True
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, nullable=False, default="free")
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="trialing"
    )  # trialing, active, past_due, canceled, unpaid
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seat_count: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
