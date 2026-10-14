"""768-dimension pgvector embeddings for documents and their sections, passed as pgvector text with an explicit cast."""
from psycopg.rows import dict_row


def vector_text(embedding):
    # pgvector text form; avoids registering a custom adapter.
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class EmbeddingRepository:
    def __init__(self, database):
        self.database = database

    async def has_sections(self, document_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT EXISTS (SELECT 1 FROM document_chunks WHERE document_id = %s)", (document_id,))
            return (await cur.fetchone())[0]

    async def save(self, document_id, sections, section_vectors, document_vector):
        """Replace a document's sections and its document-level vector in one transaction."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO document_embeddings (document_id, embedding) VALUES (%s, %s::vector)
                ON CONFLICT (document_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                (document_id, vector_text(document_vector)),
            )
            await cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
            await cur.executemany(
                "INSERT INTO document_chunks (document_id, chunk_index, content, embedding) VALUES (%s, %s, %s, %s::vector)",
                [(document_id, i, text, vector_text(vector)) for i, (text, vector) in enumerate(zip(sections, section_vectors))],
            )

    async def nearest_sections(self, workspace, embedding, limit):
        """The closest sections in the workspace, best first, with their documents."""
        vector = vector_text(embedding)
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.doc_type, d.title, d.created_by_agent, d.supersedes_id, d.source, d.drive_url, d.created_at,
                       c.chunk_index, c.content AS passage, 1 - (c.embedding <=> %s::vector) AS similarity
                FROM document_chunks c JOIN documents d ON d.id = c.document_id
                WHERE d.workspace = %s
                ORDER BY c.embedding <=> %s::vector LIMIT %s
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

