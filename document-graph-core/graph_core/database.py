"""The shared Postgres pool for every domain repository, bound once by the caller, and its readiness check."""
_database = None

# Every table the graph reads or writes, as of the newest migration. A new table goes here with its migration.
REQUIRED_TABLES = (
    "documents", "document_links", "document_embeddings", "document_chunks",
    "topics", "section_topics",
    "entity_types", "entities", "entity_aliases", "entity_mentions", "entity_relations", "relation_evidence",
    "entity_decisions", "entity_runs",
    "graph_runs", "graph_auth.records",
    "run_log", "pipeline_items", "pipeline_events", "decisions", "document_index", "run_outputs",
    "access.mcp_servers", "access.workspaces", "access.users", "access.workspace_members", "access.user_mcp_access",
)


class NotReady(RuntimeError):
    """The database isn't migrated far enough for this code, or the login can't read a table it needs."""


def configure(database):
    """Bind (or with None, unbind) the pool; the server lifespan and the job call this."""
    global _database
    _database = database


def get():
    if _database is None:
        raise RuntimeError("graph_core is not configured with a database")
    return _database


async def check_ready():
    """Raise NotReady unless every required table exists and this login can read it. One query.

    The server runs this at start-up, so an image deployed before its migration fails to start (Cloud
    Run keeps the old revision serving), rather than failing on the first call that needs a new table."""
    async with get().connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
            SELECT t.name, to_regclass(t.name) IS NOT NULL,
                   to_regclass(t.name) IS NOT NULL AND has_table_privilege(to_regclass(t.name), 'SELECT')
            FROM unnest(%s::text[]) AS t(name)
            """,
            (list(REQUIRED_TABLES),))
        rows = await cur.fetchall()
    found = {name: (exists, readable) for name, exists, readable in rows}
    missing = [t for t in REQUIRED_TABLES if not found.get(t, (False, False))[0]]
    unreadable = [t for t in REQUIRED_TABLES if t not in missing and not found[t][1]]
    if missing:
        raise NotReady(f"Document graph database is missing {', '.join(missing)}: run alembic upgrade head")
    if unreadable:
        raise NotReady(f"This database login can't read {', '.join(unreadable)}: check the migration grants")
