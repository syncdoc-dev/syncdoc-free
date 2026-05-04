"""Add workflow tables.

Revision ID: 010_add_workflow
Revises: 009_add_api_keys
Create Date: 2026-03-29 15:00:00
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "010_add_workflow"
down_revision = "009_add_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create page_workflows table
    op.create_table(
        "page_workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="draft"),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("published_by_id", sa.Integer(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["doc_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_workflows_id", "page_workflows", ["id"])
    op.create_index("ix_page_workflows_page_id", "page_workflows", ["page_id"])

    # Create page_versions table
    op.create_table(
        "page_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.Column("change_summary", sa.String(), nullable=True),
        sa.Column("workflow_state", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["doc_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_versions_id", "page_versions", ["id"])
    op.create_index("ix_page_versions_page_id", "page_versions", ["page_id"])

    # Create workflow_audit_log table
    op.create_table(
        "workflow_audit_log",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("from_state", sa.String(), nullable=True),
        sa.Column("to_state", sa.String(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["doc_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["page_workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_audit_log_id", "workflow_audit_log", ["id"])
    op.create_index("ix_workflow_audit_log_page_id", "workflow_audit_log", ["page_id"])
    op.create_index("ix_workflow_audit_log_workflow_id", "workflow_audit_log", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_audit_log_workflow_id", table_name="workflow_audit_log")
    op.drop_index("ix_workflow_audit_log_page_id", table_name="workflow_audit_log")
    op.drop_index("ix_workflow_audit_log_id", table_name="workflow_audit_log")
    op.drop_table("workflow_audit_log")

    op.drop_index("ix_page_versions_page_id", table_name="page_versions")
    op.drop_index("ix_page_versions_id", table_name="page_versions")
    op.drop_table("page_versions")

    op.drop_index("ix_page_workflows_page_id", table_name="page_workflows")
    op.drop_index("ix_page_workflows_id", table_name="page_workflows")
    op.drop_table("page_workflows")
