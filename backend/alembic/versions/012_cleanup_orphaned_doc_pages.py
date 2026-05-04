"""Cleanup orphaned doc_pages before enforcing org/project integrity

Revision ID: 012_cleanup_orphaned_doc_pages
Revises: 011_add_org_project_rbac
Create Date: 2026-04-03 15:40:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_cleanup_orphaned_doc_pages"
down_revision = "011_add_org_project_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Find a default org/project to backfill if needed
    org_id = (
        op.get_bind()
        .execute(sa.text("SELECT id FROM organizations ORDER BY created_at ASC LIMIT 1"))
        .scalar()
    )
    project_id = (
        op.get_bind()
        .execute(sa.text("SELECT id FROM projects ORDER BY created_at ASC LIMIT 1"))
        .scalar()
    )

    # Null out orphaned source references
    op.execute(
        sa.text(
            """
            UPDATE doc_pages dp
            SET source_id = NULL
            WHERE dp.source_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM sources s WHERE s.id = dp.source_id
              )
            """
        )
    )

    # Backfill org/project if any rows are still missing
    if org_id and project_id:
        op.execute(
            sa.text(
                """
                UPDATE doc_pages
                SET organization_id = :org_id,
                    project_id = :project_id
                WHERE organization_id IS NULL OR project_id IS NULL
                """
            ).bindparams(org_id=org_id, project_id=project_id)
        )


def downgrade() -> None:
    # No-op: cannot reliably restore orphaned source references
    pass
