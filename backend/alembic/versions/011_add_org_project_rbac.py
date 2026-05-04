"""Add organizations, projects, and org memberships

Revision ID: 011_add_org_project_rbac
Revises: 010_add_workflow
Create Date: 2026-04-03 13:40:00
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "011_add_org_project_rbac"
down_revision = "010_add_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"], unique=False)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_org_member"),
    )
    op.create_index(
        "ix_org_memberships_user_id",
        "organization_memberships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_org_memberships_org_id",
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )

    op.add_column("sources", sa.Column("organization_id", sa.String(), nullable=True))
    op.add_column("sources", sa.Column("project_id", sa.String(), nullable=True))
    op.create_index("ix_sources_organization_id", "sources", ["organization_id"], unique=False)
    op.create_index("ix_sources_project_id", "sources", ["project_id"], unique=False)
    op.create_foreign_key(
        "fk_sources_organization_id",
        "sources",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_sources_project_id",
        "sources",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("doc_pages", sa.Column("organization_id", sa.String(), nullable=True))
    op.add_column("doc_pages", sa.Column("project_id", sa.String(), nullable=True))
    op.create_index("ix_doc_pages_organization_id", "doc_pages", ["organization_id"], unique=False)
    op.create_index("ix_doc_pages_project_id", "doc_pages", ["project_id"], unique=False)
    op.create_foreign_key(
        "fk_doc_pages_organization_id",
        "doc_pages",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_doc_pages_project_id",
        "doc_pages",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Seed default org + project and backfill existing rows.
    org_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, created_at, updated_at)
            VALUES (:org_id, 'Default', NOW(), NOW())
            """
        ).bindparams(org_id=org_id)
    )
    op.execute(
        sa.text(
            """
            INSERT INTO projects (id, organization_id, name, created_at, updated_at)
            VALUES (:project_id, :org_id, 'General', NOW(), NOW())
            """
        ).bindparams(project_id=project_id, org_id=org_id)
    )

    op.execute(
        sa.text(
            """
            UPDATE sources
            SET organization_id = :org_id,
                project_id = :project_id
            WHERE organization_id IS NULL OR project_id IS NULL
            """
        ).bindparams(org_id=org_id, project_id=project_id)
    )

    op.execute(
        sa.text(
            """
            UPDATE doc_pages dp
            SET organization_id = s.organization_id,
                project_id = s.project_id
            FROM sources s
            WHERE dp.source_id = s.id
            """
        )
    )
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

    op.execute(
        sa.text(
            """
            INSERT INTO organization_memberships (user_id, organization_id, role, created_at)
            SELECT id, :org_id, 'member', NOW() FROM users
            """
        ).bindparams(org_id=org_id)
    )
    op.execute(
        sa.text(
            """
            UPDATE organization_memberships
            SET role = 'owner'
            WHERE user_id = (SELECT MIN(id) FROM users)
              AND organization_id = :org_id
            """
        ).bindparams(org_id=org_id)
    )

    op.alter_column("sources", "organization_id", nullable=False)
    op.alter_column("sources", "project_id", nullable=False)
    op.alter_column("doc_pages", "organization_id", nullable=False)
    op.alter_column("doc_pages", "project_id", nullable=False)


def downgrade() -> None:
    op.alter_column("doc_pages", "project_id", nullable=True)
    op.alter_column("doc_pages", "organization_id", nullable=True)
    op.drop_constraint("fk_doc_pages_project_id", "doc_pages", type_="foreignkey")
    op.drop_constraint("fk_doc_pages_organization_id", "doc_pages", type_="foreignkey")
    op.drop_index("ix_doc_pages_project_id", table_name="doc_pages")
    op.drop_index("ix_doc_pages_organization_id", table_name="doc_pages")
    op.drop_column("doc_pages", "project_id")
    op.drop_column("doc_pages", "organization_id")

    op.alter_column("sources", "project_id", nullable=True)
    op.alter_column("sources", "organization_id", nullable=True)
    op.drop_constraint("fk_sources_project_id", "sources", type_="foreignkey")
    op.drop_constraint("fk_sources_organization_id", "sources", type_="foreignkey")
    op.drop_index("ix_sources_project_id", table_name="sources")
    op.drop_index("ix_sources_organization_id", table_name="sources")
    op.drop_column("sources", "project_id")
    op.drop_column("sources", "organization_id")

    op.drop_index("ix_org_memberships_org_id", table_name="organization_memberships")
    op.drop_index("ix_org_memberships_user_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
