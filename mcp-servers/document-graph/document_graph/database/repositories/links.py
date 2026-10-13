"""Named edges between documents; duplicates are ignored."""


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
