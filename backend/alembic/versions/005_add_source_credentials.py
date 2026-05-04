"""add source_credentials table

Revision ID: 005_add_source_credentials
Revises: 004_app_settings
Create Date: 2026-03-24 21:54:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_source_credentials"
down_revision = "004_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_credentials",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("credential_type", sa.String(), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_source_credentials_source_id", "source_credentials", ["source_id"])
    op.create_index(
        "idx_source_credentials_created_by", "source_credentials", ["created_by"]
    )


def downgrade() -> None:
    op.drop_index("idx_source_credentials_created_by", table_name="source_credentials")
    op.drop_index("idx_source_credentials_source_id", table_name="source_credentials")
    op.drop_table("source_credentials")
