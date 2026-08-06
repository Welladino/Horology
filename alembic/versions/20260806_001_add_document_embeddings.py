"""add_document_embeddings

Revision ID: 20260806_001
Revises: 20260805_001
Create Date: 2026-08-06 16:47:08.563720

Adds a document_embeddings table (one row per document, 768-dim vector
from google/gemini-embedding-001 via OpenRouter, requested at 768 dims
via an undocumented-but-working `dimensions` param OpenRouter passes
through to Gemini's output_dimensionality - verified live, since the
model's un-truncated output is 3072 dims, which exceeds pgvector's
2000-dim HNSW limit) and an HNSW cosine-similarity index, for
auto-linking similar documents. Pattern (extension enable, HNSW index
built outside a transaction) matches Article_aggregator_agent's own
pgvector migrations (20260329_0002_pgvector_similarity_embedding.py,
20260410_0004_articles_socials_and_embedding_hnsw.py) - not
reinventing pgvector setup, reusing a proven approach from the sibling
project without importing its code.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260806_001'
down_revision: Union[str, Sequence[str], None] = '20260805_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "document_embeddings",
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # vector(768) isn't a native SQLAlchemy type; alter the column directly.
    op.execute("ALTER TABLE document_embeddings ALTER COLUMN embedding TYPE vector(768) USING NULL;")

    # HNSW index built outside a transaction (same pattern as the reference
    # migration) - safer rollout, avoids holding a long lock.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_document_embeddings_hnsw
            ON document_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_document_embeddings_hnsw;")
    op.drop_table("document_embeddings")
