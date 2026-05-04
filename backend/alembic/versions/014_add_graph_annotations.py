"""Add graph notes and manual edges

Revision ID: 014_add_graph_annotations
Revises: 013_add_user_theme
Create Date: 2026-04-03 21:05:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "014_add_graph_annotations"
down_revision = "013_add_user_theme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_notes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "from_node_id",
            sa.String(),
            sa.ForeignKey("infra_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "to_node_id",
            sa.String(),
            sa.ForeignKey("infra_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("color", sa.String(), nullable=False, server_default="#f59e0b"),
        sa.Column("pos_x", sa.Float(), nullable=False),
        sa.Column("pos_y", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_notes_org", "graph_notes", ["organization_id"])
    op.create_index("ix_graph_notes_project", "graph_notes", ["project_id"])
    op.create_index("ix_graph_notes_source", "graph_notes", ["source_id"])

    op.create_table(
        "graph_edges_manual",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "from_node_id",
            sa.String(),
            sa.ForeignKey("infra_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_node_id",
            sa.String(),
            sa.ForeignKey("infra_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=False, server_default="#f97316"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_edges_manual_org", "graph_edges_manual", ["organization_id"])
    op.create_index("ix_graph_edges_manual_project", "graph_edges_manual", ["project_id"])
    op.create_index("ix_graph_edges_manual_source", "graph_edges_manual", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_graph_edges_manual_source", table_name="graph_edges_manual")
    op.drop_index("ix_graph_edges_manual_project", table_name="graph_edges_manual")
    op.drop_index("ix_graph_edges_manual_org", table_name="graph_edges_manual")
    op.drop_table("graph_edges_manual")

    op.drop_index("ix_graph_notes_source", table_name="graph_notes")
    op.drop_index("ix_graph_notes_project", table_name="graph_notes")
    op.drop_index("ix_graph_notes_org", table_name="graph_notes")
    op.drop_table("graph_notes")
