"""Add theme preference to users

Revision ID: 013_add_user_theme
Revises: 012_cleanup_orphaned_doc_pages
Create Date: 2026-04-03 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "013_add_user_theme"
down_revision = "012_cleanup_orphaned_doc_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_id", sa.String(), nullable=False, server_default="original"),
    )
    op.alter_column("users", "theme_id", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "theme_id")
