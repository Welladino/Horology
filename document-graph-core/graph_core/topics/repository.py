"""Topic rows and section-to-topic assignments. Joins documents only to scope by workspace and show documents."""
from psycopg.rows import dict_row


class TopicRepository:
    def __init__(self, database):
        self.database = database

    async def assignments(self, workspace):
        """{(document_id, chunk_index): topic id} for the workspace."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT st.document_id, st.chunk_index, st.topic_id
                FROM section_topics st JOIN topics t ON t.id = st.topic_id
                WHERE t.workspace = %s
                """,
                (workspace,),
            )
            return {(doc, idx): topic for doc, idx, topic in await cur.fetchall()}

    async def topics_of(self, keys):
        """{(document_id, chunk_index): topic id} for those of the given sections that have a topic."""
        if not keys:
            return {}
        documents, indexes = zip(*keys)
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT st.document_id, st.chunk_index, st.topic_id
                FROM section_topics st JOIN unnest(%s::bigint[], %s::int[]) AS k(document_id, chunk_index)
                  ON k.document_id = st.document_id AND k.chunk_index = st.chunk_index
                """,
                (list(documents), list(indexes)),
            )
            return {(doc, idx): topic for doc, idx, topic in await cur.fetchall()}

    async def topics(self, workspace):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, name, summary, pinned FROM topics WHERE workspace = %s ORDER BY id", (workspace,))
            return await cur.fetchall()

    async def save_clustering(self, workspace, plans):
        """Replace the workspace's topics and assignments in one transaction.

        plans: [{"id": old topic id or None, "name", "summary", "members": [(doc, idx, confidence)]}].
        Old topics without a plan are deleted unless pinned. Returns the topic ids, in plan order."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM section_topics st USING topics t WHERE t.id = st.topic_id AND t.workspace = %s", (workspace,))
            kept = [plan["id"] for plan in plans if plan["id"] is not None]
            await cur.execute("DELETE FROM topics WHERE workspace = %s AND NOT pinned AND NOT (id = ANY(%s))",
                              (workspace, kept))
            ids = []
            for plan in plans:
                if plan["id"] is None:
                    await cur.execute("INSERT INTO topics (workspace, name, summary) VALUES (%s, %s, %s) RETURNING id",
                                      (workspace, plan["name"], plan["summary"]))
                    ids.append((await cur.fetchone())[0])
                else:
                    # A pinned topic keeps its name; a matched one keeps its name unless it had none.
                    await cur.execute(
                        """
                        UPDATE topics SET updated_at = now(),
                            name = CASE WHEN pinned OR name IS NOT NULL THEN name ELSE %s END,
                            summary = CASE WHEN pinned OR summary IS NOT NULL THEN summary ELSE %s END
                        WHERE id = %s AND workspace = %s
                        """,
                        (plan["name"], plan["summary"], plan["id"], workspace),
                    )
                    ids.append(plan["id"])
            rows = [(doc, idx, topic_id, confidence, "cluster")
                    for topic_id, plan in zip(ids, plans) for doc, idx, confidence in plan["members"]]
            await cur.executemany(
                "INSERT INTO section_topics (document_id, chunk_index, topic_id, confidence, assigned_by) VALUES (%s, %s, %s, %s, %s)",
                rows)
            return ids

    async def name(self, workspace, topic_id, name, summary):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE topics SET name = %s, summary = %s, updated_at = now() WHERE id = %s AND workspace = %s",
                              (name, summary, topic_id, workspace))

    async def place(self, placements):
        """Assign sections to topics: [(doc, idx, topic id, confidence)]; replaces any earlier placement."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO section_topics (document_id, chunk_index, topic_id, confidence, assigned_by)
                VALUES (%s, %s, %s, %s, 'placement')
                ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                    topic_id = EXCLUDED.topic_id, confidence = EXCLUDED.confidence, assigned_by = 'placement'
                """,
                placements)

    async def summaries(self, workspace, domain=None):
        """Each named topic with its section and document counts and the mix of document types."""
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT t.id, t.name, t.summary,
                       count(*) AS sections, count(DISTINCT d.id) AS documents,
                       (SELECT jsonb_object_agg(doc_type, n) FROM (
                            SELECT d2.doc_type, count(DISTINCT d2.id) AS n
                            FROM section_topics st2 JOIN documents d2 ON d2.id = st2.document_id
                            WHERE st2.topic_id = t.id AND (%s::text IS NULL OR d2.domain = %s)
                            GROUP BY d2.doc_type) mix) AS document_types
                FROM topics t
                JOIN section_topics st ON st.topic_id = t.id
                JOIN documents d ON d.id = st.document_id
                WHERE t.workspace = %s AND (%s::text IS NULL OR d.domain = %s)
                GROUP BY t.id
                ORDER BY count(DISTINCT d.id) DESC, t.id
                """,
                (domain, domain, workspace, domain, domain),
            )
            return await cur.fetchall()

    async def get(self, workspace, topic_id):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, name, summary, pinned FROM topics WHERE id = %s AND workspace = %s", (topic_id, workspace))
            return await cur.fetchone()

    async def documents(self, topic_id):
        """Documents in a topic with the share of their sections that fall in it."""
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id, d.title, d.doc_type, d.source, d.drive_url, d.domain, d.pipeline_id,
                       count(*) AS sections_in_topic,
                       round(count(*)::numeric / (SELECT count(*) FROM document_chunks c WHERE c.document_id = d.id), 2) AS share
                FROM section_topics st JOIN documents d ON d.id = st.document_id
                WHERE st.topic_id = %s
                GROUP BY d.id
                ORDER BY count(*) DESC, d.id
                """,
                (topic_id,),
            )
            return await cur.fetchall()

    async def strongest_sections(self, topic_id, limit):
        """The topic's highest-confidence sections, as (document_id, chunk_index, confidence)."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT document_id, chunk_index, confidence FROM section_topics WHERE topic_id = %s "
                "ORDER BY confidence DESC, document_id, chunk_index LIMIT %s",
                (topic_id, limit),
            )
            return await cur.fetchall()
