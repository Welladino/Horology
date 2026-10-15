# Psycopg 3 everywhere, and fewer database round trips

## Topic
- psycopg3-and-database-round-trips

## Context

The gateway's Neon calls used blocking Psycopg 2 inside an async server, and three Postgres drivers were in use across the services, migrations, CI and tests. Then live checks with warm instances (2026-10-13) showed slow tools: `gateway_status` 1.3 s, `list_documents` 2.3 s, `supabase_list_schema` 5.1 s. Cloud Run is in `us-central1` while Neon and Supabase are in Singapore, so each database round trip costs about 0.2 s. Moving the services to `asia-southeast1` was considered and declined.

## Decisions

**Async gateway repositories (2026-10-13).** Neon persistence moved into `database/connection.py` and `database/repositories/{quotas,cache,oauth}.py` on Psycopg 3 (3.3.6) and psycopg-pool (3.3.3). The HTTP lifespan owns an async pool of at most four connections on the serving event loop; prepared statements are off for the transaction pooler; certifi `verify-full` trust is kept. Row locks and advisory transaction locks keep reservations and token issue atomic; exceptions and cancellation roll back. 106 tests passed against disposable PostgreSQL 16 under the restricted login, including concurrent reservations across independent pools.

**Psycopg 2 removed (2026-10-13).** The Supabase adapter uses `psycopg.connect` with `verify-full`, `prepare_threshold=None` (the Supabase pooler doesn't keep prepared statements), read-only connections and `dict_row`, keeping its project and role checks, statement timeout and fixed catalog queries. `alembic/env.py` rewrites any Postgres URL to `postgresql+psycopg://`, so `.env` files need no edit. The error classifier, CI readiness check and test setup moved too, `psycopg2-binary` was removed, and the dev lock file was regenerated, picking up fixed `urllib3`, `PyJWT` and `httpx2`. All migrations ran from empty and the last four rolled back and re-applied; 150 tests passed. After release (`mcp-gateway-00009-8hr`), `gateway_status` and `supabase_list_schema` worked through the `horology-tools` plugin.

**Fewer trips per call (2026-10-13).** A verified access token is cached in memory for up to 5 minutes (never past expiry, keyed by its SHA-256, at most 256 entries, least recently used dropped first); the account check still runs every call and revocation clears the grant's entries. Five minutes covers the gaps between an agent's calls, and with one approved user the longer revocation window is acceptable. Migration `20261014_001` stores `statement_timeout=10s` and `lock_timeout=3s` as login defaults on `horology_gateway` and `horology_graph`, because PgBouncer-style poolers reject startup options; this removed two `set_config` calls per transaction, and a CI test checks both logins. The gateway reuses Supabase metadata connections through a pool of two, read-only, checked before use, dropped after 120 s idle.

**One round trip where possible (2026-10-15).** Counted from the Postgres statement log, one call of each graph tool made 80 round trips, two thirds of them `BEGIN` and `COMMIT`. `Database.connection()` now autocommits single statements; `Database.transaction()` remains for work that must succeed or fail together. `get_topic`, `find_entity`, `entity_documents` and `link_documents` each became one statement (JSON aggregation or CTEs), with byte-identical output on the trial data. Where order matters (storing sections, reserving credits, claiming runs), the statements go together as one simple query that Postgres runs as a single implicit transaction, with values quoted by `AsyncClientCursor`. A single statement can't do lock-then-check, because it reads data as of its start: 20 concurrent reservations against a cap of 3 let 4 to 10 through as one statement, but exactly 3 every time as lock-then-check in one trip; 10 concurrent run requests start exactly one run. Psycopg pipeline mode wasn't used, because its behaviour through Neon's PgBouncer is unverified.

## Rationale

One driver means one set of behaviour to know and audit. With a 0.2-second round trip, the number of trips decides latency more than anything else.

## Impact

- A call of each graph tool now makes 17 round trips instead of 80 (about 3.4 s instead of 16 s at 0.2 s each); most tools make one. An uncached paid gateway call makes 3 instead of about 13.
- A token revoked outside the process keeps working for up to 5 minutes, until a new revision or scale-to-zero clears the cache.
- Any new service login needs the same role defaults in its migration.

## Follow-Ups

- After each deploy, run `scripts/ops/live_check.py` and the latency queries and compare with the 2026-10-13 baseline.
