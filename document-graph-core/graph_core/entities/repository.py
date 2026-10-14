"""Entity rows, aliases, mentions, relations, decisions and per-document runs.

Joins documents and document_chunks only to scope by workspace and to show
documents and passages.
"""
import json

from psycopg.rows import dict_row

from ..sections.repository import vector_text


class EntityRepository:
    def __init__(self, database):
        self.database = database

    # Buckets and relationship types

    async def types(self, workspace):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, kind, name, description, position FROM entity_types WHERE workspace = %s "
                              "ORDER BY kind, position, id", (workspace,))
            return await cur.fetchall()

    async def add_types(self, workspace, kind, rows):
        """Insert missing types [(name, description)], update descriptions of existing ones."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO entity_types (workspace, kind, name, description, position) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (workspace, kind, name) DO UPDATE SET description = EXCLUDED.description, position = EXCLUDED.position
                """,
                [(workspace, kind, name, description, position) for position, (name, description) in enumerate(rows)])

    async def rename_type(self, workspace, type_id, name):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE entity_types SET name = %s WHERE id = %s AND workspace = %s", (name, type_id, workspace))

    async def move_bucket(self, workspace, from_type_id, to_type_id, suggested):
        """Move entities waiting in `other` whose suggested bucket now exists; returns how many moved."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "UPDATE entities SET type_id = %s, suggested_type = NULL, updated_at = now() "
                "WHERE workspace = %s AND type_id = %s AND lower(suggested_type) = %s AND status = 'active'",
                (to_type_id, workspace, from_type_id, suggested))
            return cur.rowcount

    # Documents waiting for extraction

    async def pending_documents(self, workspace, limit):
        """Documents whose sections changed since their last successful run (or never ran, or failed).

        Returns (document_id, sections_hash) with the hash to record once done."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                WITH current AS (
                    SELECT c.document_id, md5(string_agg(c.content, E'\\x1f' ORDER BY c.chunk_index)) AS sections_hash
                    FROM document_chunks c JOIN documents d ON d.id = c.document_id
                    WHERE d.workspace = %s
                    GROUP BY c.document_id
                )
                SELECT current.document_id, current.sections_hash
                FROM current LEFT JOIN entity_runs r ON r.document_id = current.document_id
                WHERE r.document_id IS NULL OR r.status = 'failed' OR r.sections_hash <> current.sections_hash
                ORDER BY current.document_id
                LIMIT %s
                """,
                (workspace, limit))
            return await cur.fetchall()

    async def mark_run(self, document_id, sections_hash, status):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO entity_runs (document_id, sections_hash, status) VALUES (%s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET sections_hash = EXCLUDED.sections_hash,
                    status = EXCLUDED.status, updated_at = now()
                """,
                (document_id, sections_hash, status))

    # Resolution

    async def exact(self, workspace, type_id, normalized):
        """An active entity in this bucket whose name or alias normalises to `normalized`."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT e.id FROM entity_aliases a JOIN entities e ON e.id = a.entity_id
                WHERE e.workspace = %s AND e.type_id = %s AND e.status = 'active' AND a.normalized = %s
                ORDER BY e.id LIMIT 1
                """,
                (workspace, type_id, normalized))
            row = await cur.fetchone()
            return row[0] if row else None

    async def shortlist(self, workspace, type_id, embedding, limit):
        """The closest active entities in this bucket, with their aliases."""
        vector = vector_text(embedding)
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT e.id, e.name, e.description, 1 - (e.embedding <=> %s::vector) AS similarity,
                       coalesce((SELECT array_agg(a.alias ORDER BY a.alias) FROM entity_aliases a
                                 WHERE a.entity_id = e.id AND a.normalized <> lower(e.name)), '{}') AS aliases
                FROM entities e
                WHERE e.workspace = %s AND e.type_id = %s AND e.status = 'active' AND e.embedding IS NOT NULL
                ORDER BY e.embedding <=> %s::vector LIMIT %s
                """,
                (vector, workspace, type_id, vector, limit))
            return await cur.fetchall()

    async def create(self, workspace, type_id, name, description, suggested_type, embedding, normalized):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO entities (workspace, type_id, name, description, suggested_type, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s::vector) RETURNING id",
                (workspace, type_id, name, description, suggested_type, vector_text(embedding) if embedding else None))
            entity_id = (await cur.fetchone())[0]
            await cur.execute("INSERT INTO entity_aliases (entity_id, alias, normalized) VALUES (%s, %s, %s)",
                              (entity_id, name, normalized))
            return entity_id

    async def add_alias(self, entity_id, alias, normalized):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("INSERT INTO entity_aliases (entity_id, alias, normalized) VALUES (%s, %s, %s) "
                              "ON CONFLICT DO NOTHING", (entity_id, alias, normalized))

    async def log_decisions(self, rows):
        """rows: dicts with workspace, document_id, mention, bucket, description, decision, entity_id,
        candidates, confidence, reason, model."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO entity_decisions (workspace, document_id, mention, bucket, description, decision, entity_id,
                                              candidates, confidence, reason, model)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                """,
                [(r["workspace"], r["document_id"], r["mention"], r["bucket"], r["description"], r["decision"],
                  r["entity_id"], json.dumps(r["candidates"]), r.get("confidence"), r.get("reason"), r.get("model"))
                 for r in rows])

    async def replace_document(self, document_id, mentions, relations):
        """Replace a document's mentions [(entity, section, text)] and relation evidence
        [(from entity, type id, to entity, section)] in one transaction; drop relations left without evidence."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("DELETE FROM entity_mentions WHERE document_id = %s", (document_id,))
            await cur.execute("DELETE FROM relation_evidence WHERE document_id = %s", (document_id,))
            await cur.executemany(
                "INSERT INTO entity_mentions (entity_id, document_id, chunk_index, surface) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                [(entity, document_id, section, text) for entity, section, text in mentions])
            for from_entity, type_id, to_entity, section in relations:
                await cur.execute(
                    """
                    INSERT INTO entity_relations (from_entity, type_id, to_entity) VALUES (%s, %s, %s)
                    ON CONFLICT (from_entity, type_id, to_entity) DO UPDATE SET type_id = EXCLUDED.type_id
                    RETURNING id
                    """,
                    (from_entity, type_id, to_entity))
                relation_id = (await cur.fetchone())[0]
                await cur.execute("INSERT INTO relation_evidence (relation_id, document_id, chunk_index) VALUES (%s, %s, %s) "
                                  "ON CONFLICT DO NOTHING", (relation_id, document_id, section))
            await cur.execute("DELETE FROM entity_relations r WHERE NOT EXISTS "
                              "(SELECT 1 FROM relation_evidence ev WHERE ev.relation_id = r.id)")

    # Lookups

    async def find_by_name(self, workspace, normalized, type_id=None):
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT DISTINCT e.id FROM entity_aliases a JOIN entities e ON e.id = a.entity_id
                WHERE e.workspace = %s AND e.status = 'active' AND a.normalized = %s AND (%s::bigint IS NULL OR e.type_id = %s)
                """,
                (workspace, normalized, type_id, type_id))
            return [row[0] for row in await cur.fetchall()]

    async def nearest(self, workspace, embedding, limit, type_id=None):
        vector = vector_text(embedding)
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT e.id FROM entities e
                WHERE e.workspace = %s AND e.status = 'active' AND e.embedding IS NOT NULL
                  AND (%s::bigint IS NULL OR e.type_id = %s)
                  AND EXISTS (SELECT 1 FROM entity_mentions m WHERE m.entity_id = e.id)
                ORDER BY e.embedding <=> %s::vector LIMIT %s
                """,
                (workspace, type_id, type_id, vector, limit))
            return [row[0] for row in await cur.fetchall()]

    async def cards(self, workspace, entity_ids):
        """Entities with bucket, aliases, document count and relationships, in the given order."""
        if not entity_ids:
            return []
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT e.id, e.name, t.name AS bucket, e.description, e.suggested_type,
                       coalesce((SELECT array_agg(a.alias ORDER BY a.alias) FROM entity_aliases a
                                 WHERE a.entity_id = e.id AND a.normalized <> lower(e.name)), '{}') AS aliases,
                       (SELECT count(DISTINCT m.document_id) FROM entity_mentions m WHERE m.entity_id = e.id) AS documents,
                       coalesce((SELECT jsonb_agg(jsonb_build_object(
                                     'relation', rt.name, 'direction', CASE WHEN r.from_entity = e.id THEN 'outgoing' ELSE 'incoming' END,
                                     'entity_id', o.id, 'entity', o.name,
                                     'evidence', (SELECT count(*) FROM relation_evidence ev WHERE ev.relation_id = r.id))
                                     ORDER BY rt.name, o.name)
                                 FROM entity_relations r JOIN entity_types rt ON rt.id = r.type_id
                                 JOIN entities o ON o.id = CASE WHEN r.from_entity = e.id THEN r.to_entity ELSE r.from_entity END
                                 WHERE r.from_entity = e.id OR r.to_entity = e.id), '[]') AS relationships
                FROM entities e JOIN entity_types t ON t.id = e.type_id
                WHERE e.workspace = %s AND e.id = ANY(%s)
                """,
                (workspace, list(entity_ids)))
            rows = {row["id"]: row for row in await cur.fetchall()}
            return [rows[i] for i in entity_ids if i in rows]

    async def listing(self, workspace, type_id, domain, limit):
        """Active entities with at least one mention, most documents first."""
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT e.id, e.name, t.name AS bucket, e.description, count(DISTINCT m.document_id) AS documents
                FROM entities e JOIN entity_types t ON t.id = e.type_id
                JOIN entity_mentions m ON m.entity_id = e.id JOIN documents d ON d.id = m.document_id
                WHERE e.workspace = %s AND e.status = 'active' AND (%s::bigint IS NULL OR e.type_id = %s)
                  AND (%s::text IS NULL OR d.domain = %s)
                GROUP BY e.id, t.name
                ORDER BY count(DISTINCT m.document_id) DESC, e.name
                LIMIT %s
                """,
                (workspace, type_id, type_id, domain, domain, limit))
            return await cur.fetchall()

    async def mentions(self, workspace, entity_id, limit):
        """Where an entity appears: documents with the sections naming it."""
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT d.id AS document_id, d.title, d.doc_type, d.drive_url, d.domain, d.pipeline_id,
                       m.chunk_index AS section, c.content AS text, array_agg(DISTINCT m.surface) AS named_as
                FROM entity_mentions m JOIN entities e ON e.id = m.entity_id
                JOIN documents d ON d.id = m.document_id
                JOIN document_chunks c ON c.document_id = m.document_id AND c.chunk_index = m.chunk_index
                WHERE e.workspace = %s AND m.entity_id = %s
                GROUP BY d.id, m.chunk_index, c.content
                ORDER BY d.created_at DESC, m.chunk_index
                LIMIT %s
                """,
                (workspace, entity_id, limit))
            return await cur.fetchall()

    # Review tab edits

    async def review_rows(self, workspace):
        async with self.database.transaction() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT e.id, e.name, t.name AS bucket, e.suggested_type, e.created_at,
                       coalesce((SELECT string_agg(a.alias, ', ' ORDER BY a.alias) FROM entity_aliases a
                                 WHERE a.entity_id = e.id AND a.normalized <> lower(e.name)), '') AS aliases,
                       (SELECT count(DISTINCT m.document_id) FROM entity_mentions m WHERE m.entity_id = e.id) AS documents,
                       coalesce((SELECT string_agg(DISTINCT dc.mention, ', ') FROM entity_decisions dc
                                 WHERE dc.entity_id = e.id AND dc.decision = 'same'
                                   AND dc.created_at > now() - interval '7 days'), '') AS recent_merges
                FROM entities e JOIN entity_types t ON t.id = e.type_id
                WHERE e.workspace = %s AND e.status = 'active'
                ORDER BY t.position, t.name, e.name
                """,
                (workspace,))
            return await cur.fetchall()

    async def rename(self, workspace, entity_id, name, normalized):
        """Rename an entity; the old name stays as an alias."""
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("UPDATE entities SET name = %s, updated_at = now() WHERE id = %s AND workspace = %s AND status = 'active'",
                              (name, entity_id, workspace))
            if cur.rowcount:
                await cur.execute("INSERT INTO entity_aliases (entity_id, alias, normalized) VALUES (%s, %s, %s) "
                                  "ON CONFLICT DO NOTHING", (entity_id, name, normalized))
            return bool(cur.rowcount)

    async def merge(self, workspace, source_id, target_id):
        """Fold source into target: aliases, mentions and relations move; source is kept as 'merged'."""
        if source_id == target_id:
            return False
        async with self.database.transaction() as conn, conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM entities WHERE workspace = %s AND status = 'active' AND id = ANY(%s)",
                              (workspace, [source_id, target_id]))
            if (await cur.fetchone())[0] != 2:
                return False
            await cur.execute("INSERT INTO entity_aliases (entity_id, alias, normalized) "
                              "SELECT %s, alias, normalized FROM entity_aliases WHERE entity_id = %s ON CONFLICT DO NOTHING",
                              (target_id, source_id))
            await cur.execute("INSERT INTO entity_mentions (entity_id, document_id, chunk_index, surface) "
                              "SELECT %s, document_id, chunk_index, surface FROM entity_mentions WHERE entity_id = %s "
                              "ON CONFLICT DO NOTHING", (target_id, source_id))
            await cur.execute("DELETE FROM entity_mentions WHERE entity_id = %s", (source_id,))
            await cur.execute("DELETE FROM entity_aliases WHERE entity_id = %s", (source_id,))
            # Relations: re-point to the target, merging evidence into any relation that already exists.
            await cur.execute(
                "SELECT id, from_entity, type_id, to_entity FROM entity_relations WHERE from_entity = %s OR to_entity = %s",
                (source_id, source_id))
            for relation_id, from_entity, type_id, to_entity in await cur.fetchall():
                new_from = target_id if from_entity == source_id else from_entity
                new_to = target_id if to_entity == source_id else to_entity
                if new_from == new_to:
                    await cur.execute("DELETE FROM entity_relations WHERE id = %s", (relation_id,))
                    continue
                await cur.execute(
                    "INSERT INTO entity_relations (from_entity, type_id, to_entity) VALUES (%s, %s, %s) "
                    "ON CONFLICT (from_entity, type_id, to_entity) DO UPDATE SET type_id = EXCLUDED.type_id RETURNING id",
                    (new_from, type_id, new_to))
                kept = (await cur.fetchone())[0]
                await cur.execute("INSERT INTO relation_evidence (relation_id, document_id, chunk_index) "
                                  "SELECT %s, document_id, chunk_index FROM relation_evidence WHERE relation_id = %s "
                                  "ON CONFLICT DO NOTHING", (kept, relation_id))
                await cur.execute("DELETE FROM entity_relations WHERE id = %s", (relation_id,))
            await cur.execute("UPDATE entities SET status = 'merged', merged_into = %s, updated_at = now() WHERE id = %s",
                              (target_id, source_id))
            return True
