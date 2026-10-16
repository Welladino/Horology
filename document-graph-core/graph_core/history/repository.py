"""SQL for execution history: run claims and reports, and the records pass's copies, events and outputs.

Each write is one round trip. A claim is two statements sent together as one
simple query (a single implicit transaction): a per-item lock, then the
check-and-insert, so a second claim waits and then sees the first. Values are
quoted client-side by psycopg. Every query names its workspace.
"""
from psycopg import AsyncClientCursor
from psycopg.types.json import Jsonb

ITEM_FIELDS = ("title", "domain", "type", "status", "stage", "review_stage", "agent_status", "agent_type",
               "run_location", "planner_output", "current_decision_id", "next_step")
# Pipeline fields whose changes become events, with the names they have in the sheet.
TRACKED = (("Status", "status"), ("Stage", "stage"), ("Review stage", "review_stage"),
           ("Agent status", "agent_status"), ("Agent type", "agent_type"), ("Run location", "run_location"),
           ("Planner output", "planner_output"), ("Current decision ID", "current_decision_id"),
           ("Next step / Research question", "next_step"))
DECISION_FIELDS = ("pipeline_id", "status", "review_stage", "decision", "reason", "rework_instructions")
INDEX_FIELDS = ("pipeline_id", "title", "drive_url", "doc_type", "document_status", "last_updated",
                "graph_inclusion", "graph_sync_status")

# A run "was active since the previous sync" if it started before now and hadn't ended, or its
# claim hadn't expired, by then. Used to attribute changes and outputs to a run of the same item.
_ACTIVE = """r.workspace = %(ws)s AND r.pipeline_id = {item}
    AND (r.ended_at IS NOT NULL AND r.ended_at >= coalesce(prev.at, r.started_at)
         OR r.ended_at IS NULL AND r.claim_expires >= coalesce(prev.at, now()))"""


def _columns(names):
    return ", ".join(f"{name} text" for name in names)


class HistoryRepository:
    def __init__(self, database):
        self.database = database

    async def claim(self, workspace, pipeline_id, agent, kind, run_location, hours):
        """Create a claimed run, or return the live run holding the item. -> (held_id, held_expires, new_row)."""
        async with self.database.connection() as conn, AsyncClientCursor(conn) as cur:
            await cur.execute(
                """
                SELECT pg_advisory_xact_lock(hashtext('run_log:' || %(ws)s || ':' || %(item)s));
                WITH live AS (
                    SELECT id, claim_expires FROM run_log
                    WHERE workspace = %(ws)s AND pipeline_id = %(item)s AND status IN ('claimed', 'running')
                      AND claim_expires > now()
                    ORDER BY id DESC LIMIT 1
                ), created AS (
                    INSERT INTO run_log (agent, workspace, pipeline_id, kind, run_location, status, claim_expires)
                    SELECT %(agent)s, %(ws)s, %(item)s, %(kind)s, %(location)s, 'claimed',
                           now() + make_interval(hours => %(hours)s)
                    WHERE NOT EXISTS (SELECT 1 FROM live)
                    RETURNING id, started_at, claim_expires
                )
                SELECT (SELECT id FROM live), (SELECT claim_expires FROM live),
                       (SELECT row_to_json(created) FROM created);
                """,
                {"ws": workspace, "item": pipeline_id, "agent": agent, "kind": kind, "location": run_location,
                 "hours": hours})
            cur.nextset()
            return await cur.fetchone()

    async def finish(self, workspace, run_id, status, skills_used, steps_done, notes, session_link):
        """Close an open run; returns (updated_row, existing_status) so the caller can say why not."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                WITH closed AS (
                    UPDATE run_log SET status = %(status)s, skills_used = %(skills)s, steps_done = %(steps)s,
                        summary = %(notes)s, session_link = coalesce(%(link)s, session_link),
                        ended_at = now(), reported_at = now()
                    WHERE id = %(id)s AND workspace = %(ws)s AND status IN ('claimed', 'running')
                    RETURNING id, pipeline_id, status, started_at, ended_at
                )
                SELECT (SELECT row_to_json(closed) FROM closed),
                       (SELECT status FROM run_log WHERE id = %(id)s AND workspace = %(ws)s);
                """,
                {"ws": workspace, "id": run_id, "status": status, "skills": skills_used, "steps": steps_done,
                 "notes": notes, "link": session_link})
            return await cur.fetchone()

    async def list_runs(self, workspace, since_hours, pipeline_id, limit):
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT coalesce(json_agg(x ORDER BY x.started_at DESC), '[]') FROM (
                    SELECT r.id, r.pipeline_id, r.agent AS agent_type, r.kind, r.run_location, r.status,
                           r.started_at, r.claim_expires, r.ended_at, r.reported_at, r.session_link,
                           r.skills_used, r.steps_done, r.summary AS notes,
                           (r.status IN ('claimed', 'running') AND r.claim_expires < now()) AS expired,
                           (SELECT count(*) FROM run_outputs o WHERE o.run_id = r.id) AS outputs
                    FROM run_log r
                    WHERE r.workspace = %(ws)s
                      AND (r.started_at >= now() - make_interval(hours => %(hours)s)
                           OR r.ended_at >= now() - make_interval(hours => %(hours)s))
                      AND (%(item)s::text IS NULL OR r.pipeline_id = %(item)s)
                    ORDER BY r.started_at DESC LIMIT %(limit)s
                ) x
                """,
                {"ws": workspace, "hours": since_hours, "item": pipeline_id, "limit": limit})
            return (await cur.fetchone())[0]

    async def item_history(self, workspace, pipeline_id):
        """The item's copy, events, runs (with outputs), decisions, Document Index rows and agent documents."""
        async with self.database.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                  (SELECT row_to_json(p) FROM (
                      SELECT pipeline_id, title, domain, type, status, stage, review_stage, agent_status, agent_type,
                             run_location, planner_output, current_decision_id, next_step, synced_at
                      FROM pipeline_items WHERE workspace = %(ws)s AND pipeline_id = %(item)s) p),
                  (SELECT coalesce(json_agg(e ORDER BY e.observed_at, e.id), '[]') FROM (
                      SELECT id, field, from_value, to_value, observed_at, previous_sync_at, run_id
                      FROM pipeline_events WHERE workspace = %(ws)s AND pipeline_id = %(item)s) e),
                  (SELECT coalesce(json_agg(r ORDER BY r.started_at), '[]') FROM (
                      SELECT r.id, r.agent AS agent_type, r.kind, r.run_location, r.status, r.started_at,
                             r.claim_expires, r.ended_at, r.reported_at, r.session_link, r.skills_used,
                             r.steps_done, r.summary AS notes,
                             (SELECT coalesce(json_agg(json_build_object('kind', o.kind, 'ref', o.ref)
                                                       ORDER BY o.kind, o.ref), '[]')
                              FROM run_outputs o WHERE o.run_id = r.id) AS outputs
                      FROM run_log r WHERE r.workspace = %(ws)s AND r.pipeline_id = %(item)s) r),
                  (SELECT coalesce(json_agg(d ORDER BY d.decision_id), '[]') FROM (
                      SELECT decision_id, status, review_stage, decision, reason, rework_instructions, synced_at
                      FROM decisions WHERE workspace = %(ws)s AND pipeline_id = %(item)s) d),
                  (SELECT coalesce(json_agg(i ORDER BY i.first_seen_at), '[]') FROM (
                      SELECT di.index_document_id, di.title, di.doc_type, di.document_status, di.drive_url,
                             di.last_updated, di.graph_inclusion, di.graph_sync_status, di.first_seen_at,
                             di.changed_at, g.id AS graph_document_id
                      FROM document_index di
                      LEFT JOIN documents g ON g.workspace = di.workspace AND g.source = 'sheet'
                                           AND g.index_document_id = di.index_document_id
                      WHERE di.workspace = %(ws)s AND di.pipeline_id = %(item)s) i),
                  (SELECT coalesce(json_agg(a ORDER BY a.created_at), '[]') FROM (
                      SELECT id, title, doc_type, created_by_agent, created_at
                      FROM documents WHERE workspace = %(ws)s AND source = 'agent' AND pipeline_id = %(item)s) a)
                """,
                {"ws": workspace, "item": pipeline_id})
            return await cur.fetchone()

    async def apply_records(self, workspace, items, decisions, index_rows):
        """Copy the three registers, record changes as events and link run outputs, in one transaction.

        Each argument is a list of dicts keyed like the table columns (plus "data"), or None to leave that
        copy alone. The first copy of a workspace records no events: there is nothing to compare with."""
        counts = {}
        async with self.database.transaction() as conn, conn.cursor() as cur:
            if items is not None:
                await cur.execute(_ITEMS_SQL, {"ws": workspace, "rows": Jsonb(items)})
                counts["items"], counts["item_events"] = await cur.fetchone()
            if decisions is not None:
                await cur.execute(_DECISIONS_SQL, {"ws": workspace, "rows": Jsonb(decisions)})
                counts["decisions"], counts["decision_events"] = await cur.fetchone()
            if index_rows is not None:
                await cur.execute(_INDEX_SQL, {"ws": workspace, "rows": Jsonb(index_rows)})
                counts["index_rows"], counts["index_outputs"] = await cur.fetchone()
            await cur.execute(_AGENT_OUTPUTS_SQL, {"ws": workspace})
            counts["agent_outputs"] = cur.rowcount
        return counts


_TRACKED_VALUES = ", ".join(f"('{sheet}', p.{column}, i.{column})" for sheet, column in TRACKED)

_ITEMS_SQL = f"""
WITH prev AS (SELECT max(synced_at) AS at FROM pipeline_items WHERE workspace = %(ws)s),
incoming AS (
    SELECT * FROM jsonb_to_recordset(%(rows)s) AS x(pipeline_id text, {_columns(ITEM_FIELDS)}, data jsonb)
),
changes AS (
    SELECT i.pipeline_id, f.field, f.old, f.new
    FROM incoming i
    JOIN pipeline_items p ON p.workspace = %(ws)s AND p.pipeline_id = i.pipeline_id
    CROSS JOIN LATERAL (VALUES {_TRACKED_VALUES}) AS f(field, old, new)
    WHERE f.old IS DISTINCT FROM f.new
),
events AS (
    INSERT INTO pipeline_events (workspace, pipeline_id, field, from_value, to_value, previous_sync_at, run_id)
    SELECT %(ws)s, c.pipeline_id, c.field, c.old, c.new, prev.at,
           (SELECT r.id FROM run_log r WHERE {_ACTIVE.format(item='c.pipeline_id')}
            ORDER BY r.started_at DESC LIMIT 1)
    FROM changes c CROSS JOIN prev
    RETURNING 1
),
upserted AS (
    INSERT INTO pipeline_items (workspace, pipeline_id, {", ".join(ITEM_FIELDS)}, data, synced_at)
    SELECT %(ws)s, pipeline_id, coalesce(title, ''), {", ".join(ITEM_FIELDS[1:])}, coalesce(data, '{{}}'), now()
    FROM incoming
    ON CONFLICT (workspace, pipeline_id) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in ITEM_FIELDS)}, data = EXCLUDED.data, synced_at = now()
    RETURNING 1
)
SELECT (SELECT count(*) FROM upserted), (SELECT count(*) FROM events)
"""  # nosec B608: SQL text is built from fixed column names in code; values are bound parameters

_DECISIONS_SQL = f"""
WITH prev AS (SELECT max(synced_at) AS at FROM decisions WHERE workspace = %(ws)s),
incoming AS (
    SELECT * FROM jsonb_to_recordset(%(rows)s) AS x(decision_id text, {_columns(DECISION_FIELDS)}, data jsonb)
),
changes AS (
    SELECT i.decision_id, i.pipeline_id, d.status AS old, i.status AS new
    FROM incoming i
    LEFT JOIN decisions d ON d.workspace = %(ws)s AND d.decision_id = i.decision_id
    CROSS JOIN prev
    WHERE prev.at IS NOT NULL AND i.pipeline_id IS NOT NULL AND d.status IS DISTINCT FROM i.status
),
events AS (
    INSERT INTO pipeline_events (workspace, pipeline_id, field, from_value, to_value, previous_sync_at, run_id)
    SELECT %(ws)s, c.pipeline_id, 'Decision ' || c.decision_id || ' status', c.old, c.new, prev.at,
           (SELECT r.id FROM run_log r WHERE {_ACTIVE.format(item='c.pipeline_id')}
            ORDER BY r.started_at DESC LIMIT 1)
    FROM changes c CROSS JOIN prev
    RETURNING 1
),
upserted AS (
    INSERT INTO decisions (workspace, decision_id, {", ".join(DECISION_FIELDS)}, data, synced_at)
    SELECT %(ws)s, decision_id, {", ".join(DECISION_FIELDS)}, coalesce(data, '{{}}'), now() FROM incoming
    ON CONFLICT (workspace, decision_id) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in DECISION_FIELDS)}, data = EXCLUDED.data, synced_at = now()
    RETURNING 1
)
SELECT (SELECT count(*) FROM upserted), (SELECT count(*) FROM events)
"""  # nosec B608: SQL text is built from fixed column names in code; values are bound parameters

_INDEX_COLUMNS = ", ".join(f"{c} text" if c != "graph_inclusion" else "graph_inclusion boolean" for c in INDEX_FIELDS)

_INDEX_SQL = f"""
WITH prev AS (SELECT max(synced_at) AS at FROM document_index WHERE workspace = %(ws)s),
incoming AS (
    SELECT * FROM jsonb_to_recordset(%(rows)s) AS x(index_document_id text, {_INDEX_COLUMNS}, data jsonb)
),
changed AS (
    SELECT i.index_document_id, i.pipeline_id FROM incoming i
    LEFT JOIN document_index d ON d.workspace = %(ws)s AND d.index_document_id = i.index_document_id
    WHERE d.index_document_id IS NULL OR d.data IS DISTINCT FROM coalesce(i.data, '{{}}')
),
outputs AS (
    INSERT INTO run_outputs (run_id, kind, ref)
    SELECT r.id, 'index', c.index_document_id
    FROM changed c CROSS JOIN prev
    JOIN run_log r ON {_ACTIVE.format(item='c.pipeline_id')}
    WHERE c.pipeline_id IS NOT NULL
    ON CONFLICT DO NOTHING
    RETURNING 1
),
upserted AS (
    INSERT INTO document_index (workspace, index_document_id, {", ".join(INDEX_FIELDS)}, data, synced_at)
    SELECT %(ws)s, index_document_id, pipeline_id, coalesce(title, ''), drive_url, doc_type, document_status,
           last_updated, coalesce(graph_inclusion, false), graph_sync_status, coalesce(data, '{{}}'), now()
    FROM incoming
    ON CONFLICT (workspace, index_document_id) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in INDEX_FIELDS)}, data = EXCLUDED.data, synced_at = now(),
        changed_at = CASE WHEN document_index.data IS DISTINCT FROM EXCLUDED.data THEN now()
                          ELSE document_index.changed_at END
    RETURNING 1
)
SELECT (SELECT count(*) FROM upserted), (SELECT count(*) FROM outputs)
"""  # nosec B608: SQL text is built from fixed column names in code; values are bound parameters

_AGENT_OUTPUTS_SQL = """
INSERT INTO run_outputs (run_id, kind, ref)
SELECT r.id, 'agent', d.id::text
FROM run_log r
JOIN documents d ON d.workspace = r.workspace AND d.source = 'agent' AND d.pipeline_id = r.pipeline_id
                AND d.created_at >= r.started_at AND d.created_at <= coalesce(r.ended_at, r.claim_expires)
WHERE r.workspace = %(ws)s
ON CONFLICT DO NOTHING
"""
