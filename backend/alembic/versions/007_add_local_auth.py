"""Add local authentication support to users table.

Revision ID: 007_local_auth
Revises: 006_users
Create Date: 2026-03-25

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "007_local_auth"
down_revision = "006_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make github_id nullable
    op.alter_column(
        "users",
        "github_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    # Make github_access_token nullable
    op.alter_column(
        "users",
        "github_access_token",
        existing_type=sa.Text(),
        nullable=True,
    )

    # Add password_hash column
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=True),
    )

    # Add auth_provider column
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(), nullable=False, server_default="local"),
    )

    # Add unique constraint to email
    op.create_unique_constraint(
        "uq_users_email",
        "users",
        ["email"],
    )

    # Create index on email
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
    )


def downgrade() -> None:
    # Drop email index
    op.drop_index("ix_users_email", table_name="users")

    # Drop email unique constraint
    op.drop_constraint("uq_users_email", "users", type_="unique")

    # Drop auth_provider column
    op.drop_column("users", "auth_provider")

    # Drop password_hash column
    op.drop_column("users", "password_hash")

    # Make github_access_token not nullable
    op.alter_column(
        "users",
        "github_access_token",
        existing_type=sa.Text(),
        nullable=False,
    )

    # Make github_id not nullable
    op.alter_column(
        "users",
        "github_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
