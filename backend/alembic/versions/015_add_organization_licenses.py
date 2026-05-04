"""Add organization licenses

Revision ID: 015_add_organization_licenses
Revises: 014_add_graph_annotations
Create Date: 2026-04-04 23:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "015_add_organization_licenses"
down_revision = "014_add_graph_annotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_licenses",
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("license_id", sa.String(), nullable=True),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("license_token", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("organization_licenses")
