"""Add app_settings table for runtime configuration

Revision ID: 004_app_settings
Revises: 003_tz_aware
Create Date: 2026-03-24 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "004_app_settings"
down_revision = "003_tz_aware"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
