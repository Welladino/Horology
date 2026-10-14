"""Document rows and document-to-document links; every document query names its workspace."""
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

    # Document Index sync. Sheet rows are keyed by workspace + Index Document ID.

    async def sheet_documents(self, workspace):
        """Return {index_document_id: (graph id, imported Drive revision)} for sheet rows."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT index_document_id, id, source_revision FROM documents WHERE workspace = %s AND source = 'sheet'",
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
        """Remove sheet documents (their sections, vectors and links cascade); returns the ids removed."""
        if not index_document_ids:
            return []
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM documents WHERE workspace = %s AND source = 'sheet' AND index_document_id = ANY(%s) RETURNING index_document_id",
                (workspace, list(index_document_ids)),
            )
            return [row[0] for row in await cur.fetchall()]


class LinkRepository:
    def __init__(self, database):
        self.database = database

    async def add(self, from_doc_id, to_doc_id, relation):
        """Return the new link id, or None when the edge already exists."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO document_links (from_doc_id, to_doc_id, relation)
                VALUES (%s, %s, %s)
                ON CONFLICT (from_doc_id, to_doc_id, relation) DO NOTHING
                RETURNING id
                """,
                (from_doc_id, to_doc_id, relation),
            )
            row = await cur.fetchone()
            return row[0] if row else None
