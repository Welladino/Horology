"""Document sections with their own embeddings, for passage search.

Each document is split into sections of up to ~2,000 characters; every
section has its own 768-dimension embedding. Search ranks sections and returns
each matching document with its best passages. document_embeddings stays as
the document-level vector (the mean of its sections) used for auto-linking.
Sections are rebuilt whenever a document is re-embedded and cascade on delete.
"""
from alembic import op

revision = '20261014_002'
down_revision = '20261014_001'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE document_chunks (
            document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL CHECK (chunk_index >= 0),
            content text NOT NULL,
            embedding vector(768) NOT NULL,
            PRIMARY KEY (document_id, chunk_index)
        )
    """)
    op.execute('CREATE INDEX document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)')
    op.execute('GRANT SELECT, INSERT, DELETE ON document_chunks TO horology_graph')
    op.execute('GRANT SELECT ON document_chunks TO horology_cron_sweep_ro')


def downgrade():
    op.execute('DROP TABLE document_chunks')
