"""Section rows (document_chunks) and document vectors (document_embeddings).

768-dimension pgvector embeddings, passed as pgvector text with an explicit
cast. Joins documents only to scope by workspace and to show titles."""
from psycopg.rows import dict_row


def vector_text(embedding):
    # pgvector text form; avoids registering a custom adapter.
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class SectionRepository:
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

    async def nearest_sections(self, workspace, embedding, limit, domain=None):
        """The closest sections in the workspace (optionally one domain), best first, with their documents."""
        vector = vector_text(embedding)
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.doc_type, d.title, d.created_by_agent, d.supersedes_id, d.source, d.drive_url, d.created_at,
                       d.domain, d.business_entity, d.pipeline_id,
                       c.chunk_index, c.content AS passage, 1 - (c.embedding <=> %s::vector) AS similarity
                FROM document_chunks c JOIN documents d ON d.id = c.document_id
                WHERE d.workspace = %s AND (%s::text IS NULL OR d.domain = %s)
                ORDER BY c.embedding <=> %s::vector LIMIT %s
                """,
                (vector, workspace, domain, domain, vector, limit),
            )
            return await cur.fetchall()

    async def with_sections(self, document_ids):
        """The subset of document_ids that have at least one section."""
        if not document_ids:
            return set()
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT DISTINCT document_id FROM document_chunks WHERE document_id = ANY(%s)", (list(document_ids),))
            return {row[0] for row in await cur.fetchall()}

    async def documents_without_sections(self, workspace):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.title, d.doc_type, d.created_at
                FROM documents d
                WHERE d.workspace = %s AND NOT EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = d.id)
                ORDER BY d.created_at
                """,
                (workspace,),
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

    async def neighbour_links(self, workspace, k, floor, document_id=None):
        """Each section's k nearest sections in other documents of the workspace, at or above floor.

        Returns (document_id, chunk_index, neighbour document_id, neighbour chunk_index, similarity).
        With document_id, only that document's sections are the starting points."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT c.document_id, c.chunk_index, n.document_id, n.chunk_index, n.similarity
                FROM document_chunks c JOIN documents d ON d.id = c.document_id
                CROSS JOIN LATERAL (
                    SELECT c2.document_id, c2.chunk_index, 1 - (c2.embedding <=> c.embedding) AS similarity
                    FROM document_chunks c2 JOIN documents d2 ON d2.id = c2.document_id
                    WHERE d2.workspace = d.workspace AND c2.document_id <> c.document_id
                    ORDER BY c2.embedding <=> c.embedding LIMIT %s
                ) n
                WHERE d.workspace = %s AND (%s::bigint IS NULL OR c.document_id = %s) AND n.similarity >= %s
                """,
                (k, workspace, document_id, document_id, floor),
            )
            return await cur.fetchall()

    async def texts(self, keys):
        """{(document_id, chunk_index): section text} for the given sections."""
        if not keys:
            return {}
        documents, indexes = zip(*keys)
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT c.document_id, c.chunk_index, c.content
                FROM document_chunks c JOIN unnest(%s::bigint[], %s::int[]) AS k(document_id, chunk_index)
                  ON k.document_id = c.document_id AND k.chunk_index = c.chunk_index
                """,
                (list(documents), list(indexes)),
            )
            return {(doc, idx): text for doc, idx, text in await cur.fetchall()}

