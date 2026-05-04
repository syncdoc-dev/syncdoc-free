"""Add users table and user_id FK column to sources

Revision ID: 006_users
Revises: 005_add_source_credentials
Create Date: 2026-03-24 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "006_users"
down_revision = "005_add_source_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.String(), nullable=True),
        sa.Column("github_access_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)
    op.create_index(op.f("ix_users_login"), "users", ["login"], unique=True)

    op.add_column(
        "sources",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_sources_user_id"), "sources", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_sources_user_id_users",
        "sources",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_sources_user_id_users", "sources", type_="foreignkey")
    op.drop_index(op.f("ix_sources_user_id"), table_name="sources")
    op.drop_column("sources", "user_id")

    op.drop_index(op.f("ix_users_login"), table_name="users")
    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
