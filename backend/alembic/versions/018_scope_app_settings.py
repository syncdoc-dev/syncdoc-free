"""Scope runtime settings to organizations.

Revision ID: 018_scope_app_settings
Revises: 017_add_subscriptions
"""

import sqlalchemy as sa

from alembic import op

revision = "018_scope_app_settings"
down_revision = "017_add_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings_v2",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.String(), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("organization_id", "key", name="uq_app_setting_org_key"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO app_settings_v2 (organization_id, key, value, updated_at)
            SELECT NULL, key, value, updated_at FROM app_settings
            """
        )
    )
    op.drop_table("app_settings")
    op.rename_table("app_settings_v2", "app_settings")
    op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=False)
    op.create_index(
        "ix_app_settings_organization_id",
        "app_settings",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.create_table(
        "app_settings_v1",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO app_settings_v1 (key, value, updated_at)
            SELECT DISTINCT ON (key) key, value, updated_at
            FROM app_settings
            ORDER BY key, organization_id NULLS FIRST
            """
        )
    )
    op.drop_table("app_settings")
    op.rename_table("app_settings_v1", "app_settings")
