"""768-dimension pgvector embeddings, passed as pgvector text with an explicit cast."""
from psycopg.rows import dict_row


def vector_text(embedding):
    # pgvector text form; avoids registering a custom adapter.
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class EmbeddingRepository:
    def __init__(self, database):
        self.database = database

    async def exists(self, document_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT embedding IS NOT NULL FROM document_embeddings WHERE document_id = %s", (document_id,))
            row = await cur.fetchone()
            return bool(row and row[0])

    async def save(self, document_id, embedding):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO document_embeddings (document_id, embedding) VALUES (%s, %s::vector)
                ON CONFLICT (document_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                (document_id, vector_text(embedding)),
            )

    async def nearest(self, workspace, embedding, limit):
        vector = vector_text(embedding)
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.doc_type, d.title, d.created_by_agent, d.supersedes_id, d.source, d.drive_url, d.created_at,
                       1 - (e.embedding <=> %s::vector) AS similarity
                FROM document_embeddings e JOIN documents d ON d.id = e.document_id
                WHERE d.workspace = %s AND e.embedding IS NOT NULL
                ORDER BY e.embedding <=> %s::vector LIMIT %s
                """,
                (vector, workspace, vector, limit),
            )
            return await cur.fetchall()

    async def similar_to(self, workspace, document_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT e.document_id, 1 - (e.embedding <=> (
                    SELECT embedding FROM document_embeddings WHERE document_id = %s
                )) AS similarity
                FROM document_embeddings e JOIN documents d ON d.id = e.document_id
                WHERE e.document_id != %s AND e.embedding IS NOT NULL AND d.workspace = %s
                ORDER BY similarity DESC
                """,
                (document_id, document_id, workspace),
            )
            return await cur.fetchall()
