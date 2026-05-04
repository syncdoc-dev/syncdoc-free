"""Replace placeholder UUID embedding column with pgvector vector(768).

Revision ID: 008_add_vector_embedding
Revises: 007_local_auth
Create Date: 2026-03-25

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_add_vector_embedding"
down_revision = "007_local_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the placeholder UUID embedding column
    op.drop_column("doc_pages", "embedding")

    # Add the real vector(1536) column for OpenAI embeddings.
    # Raw SQL is required because SQLAlchemy dialects don't know pgvector yet.
    op.execute("ALTER TABLE doc_pages ADD COLUMN embedding vector(1536)")

    # HNSW index for fast cosine similarity search
    op.execute(
        "CREATE INDEX idx_doc_pages_embedding ON doc_pages USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_pages_embedding")
    op.drop_column("doc_pages", "embedding")

    # Restore the original placeholder UUID column
    op.execute("ALTER TABLE doc_pages ADD COLUMN embedding uuid")
