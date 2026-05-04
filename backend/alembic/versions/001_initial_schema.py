"""Initial schema setup with all core tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("credentials_ref", sa.String(), nullable=True),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create infra_nodes table
    op.create_table(
        "infra_nodes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("config_json", postgresql.JSON(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create infra_edges table
    op.create_table(
        "infra_edges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("from_node_id", sa.String(), nullable=False),
        sa.Column("to_node_id", sa.String(), nullable=False),
        sa.Column("relation_type", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["from_node_id"], ["infra_nodes.id"]),
        sa.ForeignKeyConstraint(["to_node_id"], ["infra_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create doc_pages table
    op.create_table(
        "doc_pages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_md", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("embedding", postgresql.UUID(), nullable=True),
        sa.Column("is_manually_edited", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create drift_events table
    op.create_table(
        "drift_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("page_id", sa.String(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("diff_json", postgresql.JSON(), nullable=False),
        sa.Column("resolved", sa.Integer(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["infra_nodes.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["doc_pages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create sync_runs table
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("nodes_added", sa.Integer(), nullable=False),
        sa.Column("nodes_updated", sa.Integer(), nullable=False),
        sa.Column("drift_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_infra_nodes_source_id", "infra_nodes", ["source_id"])
    op.create_index("idx_infra_nodes_kind", "infra_nodes", ["kind"])
    op.create_index("idx_infra_edges_from", "infra_edges", ["from_node_id"])
    op.create_index("idx_infra_edges_to", "infra_edges", ["to_node_id"])
    op.create_index("idx_drift_events_node_id", "drift_events", ["node_id"])
    op.create_index("idx_drift_events_resolved", "drift_events", ["resolved"])
    op.create_index("idx_sync_runs_source_id", "sync_runs", ["source_id"])


def downgrade() -> None:
    op.drop_index("idx_sync_runs_source_id", table_name="sync_runs")
    op.drop_index("idx_drift_events_resolved", table_name="drift_events")
    op.drop_index("idx_drift_events_node_id", table_name="drift_events")
    op.drop_index("idx_infra_edges_to", table_name="infra_edges")
    op.drop_index("idx_infra_edges_from", table_name="infra_edges")
    op.drop_index("idx_infra_nodes_kind", table_name="infra_nodes")
    op.drop_index("idx_infra_nodes_source_id", table_name="infra_nodes")

    op.drop_table("sync_runs")
    op.drop_table("drift_events")
    op.drop_table("doc_pages")
    op.drop_table("infra_edges")
    op.drop_table("infra_nodes")
    op.drop_table("sources")

    op.execute("DROP EXTENSION IF EXISTS vector")
