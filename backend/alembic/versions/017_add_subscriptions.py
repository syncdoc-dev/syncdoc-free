"""Add subscriptions table for Stripe billing

Revision ID: 017_add_subscriptions
Revises: 016_password_reset_marketing
Create Date: 2026-05-27 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "017_add_subscriptions"
down_revision = "016_password_reset_marketing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True, unique=True),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("status", sa.String(), nullable=False, server_default="trialing"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seat_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_table("subscriptions")
