"""Section rows (document_chunks) and document vectors (document_embeddings).

768-dimension pgvector embeddings, passed as pgvector text with an explicit
cast. Joins documents only to scope by workspace and to show titles."""
from psycopg import AsyncClientCursor
from psycopg.rows import dict_row


def vector_text(embedding):
    # pgvector text form; avoids registering a custom adapter.
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class SectionRepository:
    def __init__(self, database):
        self.database = database

    async def has_sections(self, document_id):
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT EXISTS (SELECT 1 FROM document_chunks WHERE document_id = %s)", (document_id,))
            return (await cur.fetchone())[0]

    async def to_embed(self, workspace, document_id):
        """(title, content, has sections) for a document in the workspace, in one query; None if there's none."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT d.title, d.content, EXISTS (SELECT 1 FROM document_chunks c WHERE c.document_id = d.id) "
                "FROM documents d WHERE d.id = %s AND d.workspace = %s", (document_id, workspace))
            return await cur.fetchone()

    async def save(self, document_id, sections, section_vectors, document_vector):
        """Replace a document's sections and its document-level vector, all or nothing, in one round trip.

        The statements go together as one simple query, which Postgres runs as a single implicit
        transaction. Values are quoted client-side by psycopg (the extended protocol takes one
        statement per message). Old sections are deleted, not updated, so topic placements and
        entity mentions of changed text go with them."""
        rows = [(i, text, vector_text(vector)) for i, (text, vector) in enumerate(zip(sections, section_vectors))]
        values = ", ".join(["(%s, %s, %s, %s::vector)"] * len(rows))
        async with self.database.connection() as conn, AsyncClientCursor(conn) as cur:
            await cur.execute(
                "INSERT INTO document_embeddings (document_id, embedding) VALUES (%s, %s::vector) "
                "ON CONFLICT (document_id) DO UPDATE SET embedding = EXCLUDED.embedding; "
                "DELETE FROM document_chunks WHERE document_id = %s; "  # nosec B608: SQL text is fixed in code; values are bound parameters
                + (f"INSERT INTO document_chunks (document_id, chunk_index, content, embedding) VALUES {values};" if rows else ""),  # nosec B608: SQL text is fixed in code; values are bound parameters
                [document_id, vector_text(document_vector), document_id]
                + [value for index, text, vector in rows for value in (document_id, index, text, vector)],
            )

    async def nearest_sections(self, workspace, embedding, limit, domain=None):
        """The closest sections in the workspace (optionally one domain), best first, with their documents."""
        vector = vector_text(embedding)
        async with self.database.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
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
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT DISTINCT document_id FROM document_chunks WHERE document_id = ANY(%s)", (list(document_ids),))
            return {row[0] for row in await cur.fetchall()}

    async def documents_without_sections(self, workspace):
        async with self.database.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
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
        async with self.database.connection() as conn, conn.cursor() as cur:
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

    async def document_ids(self, workspace):
        """Ids of the workspace's documents that have sections, in order."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT c.document_id FROM document_chunks c JOIN documents d ON d.id = c.document_id "
                "WHERE d.workspace = %s ORDER BY c.document_id", (workspace,))
            return [row[0] for row in await cur.fetchall()]

    async def neighbour_links(self, workspace, k, floor, document_ids):
        """Each section's k nearest sections in other documents of the workspace, at or above floor,
        starting from the sections of document_ids only.

        Returns (document_id, chunk_index, neighbour document_id, neighbour chunk_index, similarity)."""
        async with self.database.connection() as conn, conn.cursor() as cur:
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
                WHERE d.workspace = %s AND c.document_id = ANY(%s) AND n.similarity >= %s
                """,
                (k, workspace, list(document_ids), floor),
            )
            return await cur.fetchall()

    async def texts(self, keys):
        """{(document_id, chunk_index): section text} for the given sections."""
        if not keys:
            return {}
        documents, indexes = zip(*keys)
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT c.document_id, c.chunk_index, c.content
                FROM document_chunks c JOIN unnest(%s::bigint[], %s::int[]) AS k(document_id, chunk_index)
                  ON k.document_id = c.document_id AND k.chunk_index = c.chunk_index
                """,
                (list(documents), list(indexes)),
            )
            return {(doc, idx): text for doc, idx, text in await cur.fetchall()}

    async def of_document(self, document_id):
        """[(chunk_index, text)] for one document, in order."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute("SELECT chunk_index, content FROM document_chunks WHERE document_id = %s ORDER BY chunk_index",
                              (document_id,))
            return await cur.fetchall()

