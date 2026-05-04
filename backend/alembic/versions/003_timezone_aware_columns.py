"""Make sync_runs and drift_events datetime columns timezone-aware

Revision ID: 003_tz_aware
Revises: 002_add_source_id
Create Date: 2026-03-22 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_tz_aware"
down_revision = "002_add_source_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # sync_runs: convert naive datetime columns to timezone-aware
    for col in ["started_at", "completed_at"]:
        op.alter_column(
            "sync_runs",
            col,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=col == "completed_at",
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )

    # drift_events: convert naive datetime columns to timezone-aware
    for col in ["detected_at", "resolved_at", "created_at"]:
        op.alter_column(
            "drift_events",
            col,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=col == "resolved_at",
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for col in ["started_at", "completed_at"]:
        op.alter_column(
            "sync_runs",
            col,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=col == "completed_at",
        )

    for col in ["detected_at", "resolved_at", "created_at"]:
        op.alter_column(
            "drift_events",
            col,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=col == "resolved_at",
        )
