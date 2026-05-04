"""Add source_id column to doc_pages

Revision ID: 002_add_source_id
Revises: 001_initial_schema
Create Date: 2026-03-16 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_source_id"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "doc_pages",
        sa.Column("source_id", sa.String(), sa.ForeignKey("sources.id"), nullable=True),
    )
    op.create_index("idx_doc_pages_source_id", "doc_pages", ["source_id"])


def downgrade() -> None:
    op.drop_index("idx_doc_pages_source_id", table_name="doc_pages")
    op.drop_column("doc_pages", "source_id")
