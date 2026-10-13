"""Document rows; every query names its workspace."""
from psycopg.rows import dict_row

SUMMARY_COLUMNS = "id, doc_type, title, created_by_agent, supersedes_id, source, drive_url, created_at"


class DocumentRepository:
    def __init__(self, database):
        self.database = database

    async def insert_agent_document(self, workspace, doc_type, title, content, created_by_agent, supersedes_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO documents (doc_type, title, content, created_by_agent, supersedes_id, workspace, source)
                VALUES (%s, %s, %s, %s, %s, %s, 'agent')
                RETURNING id, created_at
                """,
                (doc_type, title, content, created_by_agent, supersedes_id, workspace),
            )
            return await cur.fetchone()

    async def count_existing(self, workspace, ids):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM documents WHERE id = ANY(%s) AND workspace = %s", (list(ids), workspace))
            return (await cur.fetchone())[0]

    async def get(self, workspace, document_id):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, doc_type, title, content, created_by_agent, supersedes_id, source, drive_url, created_at
                FROM documents WHERE id = %s AND workspace = %s
                """,
                (document_id, workspace),
            )
            return await cur.fetchone()

    async def content(self, workspace, document_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT content FROM documents WHERE id = %s AND workspace = %s", (document_id, workspace))
            row = await cur.fetchone()
            return row[0] if row else None

    async def list(self, workspace, doc_type, limit):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"""
                SELECT {SUMMARY_COLUMNS} FROM documents
                WHERE workspace = %s AND (%s::text IS NULL OR doc_type = %s)
                ORDER BY created_at DESC LIMIT %s
                """,
                (workspace, doc_type, doc_type, limit),
            )
            return await cur.fetchall()

    async def related(self, workspace, document_id):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.title, d.doc_type, l.relation, 'outgoing' AS direction
                FROM document_links l JOIN documents d ON d.id = l.to_doc_id
                WHERE l.from_doc_id = %s AND d.workspace = %s
                UNION ALL
                SELECT d.id, d.title, d.doc_type, l.relation, 'incoming' AS direction
                FROM document_links l JOIN documents d ON d.id = l.from_doc_id
                WHERE l.to_doc_id = %s AND d.workspace = %s
                """,
                (document_id, workspace, document_id, workspace),
            )
            return await cur.fetchall()

    async def unembedded(self, workspace):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.title, d.doc_type, d.created_at
                FROM documents d
                LEFT JOIN document_embeddings e ON e.document_id = d.id
                WHERE e.document_id IS NULL AND d.workspace = %s
                ORDER BY d.created_at
                """,
                (workspace,),
            )
            return await cur.fetchall()

    # Document Index sync. Sheet rows are keyed by workspace + Index Document ID.

    async def sheet_revisions(self, workspace):
        """Return {index_document_id: (graph id, imported Drive revision or None)} for sheet rows.

        The revision is None when the document has no embedding yet, so a row
        whose earlier import stopped before embedding is imported again."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT d.index_document_id, d.id,
                       CASE WHEN e.embedding IS NOT NULL THEN d.source_revision END
                FROM documents d LEFT JOIN document_embeddings e ON e.document_id = d.id
                WHERE d.workspace = %s AND d.source = 'sheet'
                """,
                (workspace,),
            )
            return {index_id: (doc_id, revision) for index_id, doc_id, revision in await cur.fetchall()}

    async def upsert_sheet_document(self, workspace, index_document_id, drive_file_id, drive_url, doc_type, title, content, revision):
        """Insert or replace one sheet document; returns its graph id."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO documents (doc_type, title, content, created_by_agent, workspace, source,
                                       index_document_id, drive_file_id, drive_url, source_revision, synced_at)
                VALUES (%s, %s, %s, 'document-index-sync', %s, 'sheet', %s, %s, %s, %s, now())
                ON CONFLICT (workspace, index_document_id) WHERE source = 'sheet' DO UPDATE SET
                    doc_type = EXCLUDED.doc_type, title = EXCLUDED.title, content = EXCLUDED.content,
                    drive_file_id = EXCLUDED.drive_file_id, drive_url = EXCLUDED.drive_url,
                    source_revision = EXCLUDED.source_revision, synced_at = now()
                RETURNING id
                """,
                (doc_type, title, content, workspace, index_document_id, drive_file_id, drive_url, revision),
            )
            return (await cur.fetchone())[0]

    async def set_supersedes(self, workspace, document_id, supersedes_id):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE documents SET supersedes_id = %s WHERE id = %s AND workspace = %s",
                              (supersedes_id, document_id, workspace))

    async def delete_sheet_documents(self, workspace, index_document_ids):
        """Remove sheet documents (their embeddings and links cascade); returns the ids removed."""
        if not index_document_ids:
            return []
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM documents WHERE workspace = %s AND source = 'sheet' AND index_document_id = ANY(%s) RETURNING index_document_id",
                (workspace, list(index_document_ids)),
            )
            return [row[0] for row in await cur.fetchall()]
