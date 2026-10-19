# Alembic / Neon Workflow

How the document-graph database (Neon Postgres: `documents`, `document_links`, `run_log`) is migrated and connected to. Design rationale is in [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](../../planning/notes/2026-08-05_horology-founding-decisions_note.md) — this doc is the practical how-to only.

## One-time setup

One shared venv at the repo root covers Alembic and editor/import resolution for `mcp-servers/` — not a separate venv per component.

```bash
cd Horology
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.lock.txt
```

`.venv/` is gitignored — every machine that runs migrations sets this up locally, it's not committed. Point your editor's Python interpreter at `Horology/.venv/bin/python` for the whole repo, including files under `mcp-servers/`.

Install from `requirements-dev.lock.txt` (the full pinned set, direct + transitive), not `requirements-dev.txt` (the short human-edited list of what's actually depended on directly) — the lockfile guarantees the exact same versions get installed on any machine, rather than whatever the latest compatible transitive versions happen to be at install time. If you add/change a direct dependency, edit `requirements-dev.txt`, then regenerate the lockfile (`pip install -r requirements-dev.txt && pip freeze > requirements-dev.lock.txt`) and re-run the test suite before committing both files.

## Connection strings — direct vs. pooled, and why both exist

Neon gives you two connection strings for the same database:

- **Direct** (no `-pooler` in the hostname) — used for **Alembic migrations only**. Transaction-mode pooling (see below) doesn't support everything a migration may need (e.g. `CREATE INDEX CONCURRENTLY`, session-level `SET`).
- **Pooled** (`-pooler` in the hostname, PgBouncer in transaction mode) — used by Hermes's own runtime doc-graph queries later (via MCP). Short-lived queries from an agent are exactly the case a transaction pooler is for.

Both go in `.env` (gitignored, never committed — copy from `.env.example` and fill in real values):

```bash
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
DATABASE_URL_POOLED=postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/dbname?sslmode=require
```

`alembic/env.py` reads `DATABASE_URL` (the direct one) automatically — nothing to configure per-run. `DATABASE_URL_POOLED` isn't used by Alembic; it's there so it's ready when the doc-graph MCP tool is wired up.

## Running migrations

```bash
source .venv/bin/activate

# Apply all pending migrations
alembic upgrade head

# Check current DB revision vs. what's in alembic/versions/
alembic current
alembic history
```

### Migrations that need extra env vars

Most migrations only need `DATABASE_URL`. `20260807_001_add_readonly_role_for_cron_sweep.py` also requires `CRON_SWEEP_RO_PASSWORD` (the password for the new read-only role it creates) — it raises immediately if unset rather than inventing or hardcoding one:

```bash
CRON_SWEEP_RO_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')" alembic upgrade head
```

After running it, build the connection string by hand (Neon's pooled hostname, same host/db as `DATABASE_URL_POOLED` but with the new role's name/password) and add it to `.env` as `CRON_SWEEP_RO_DATABASE_URL` — see `.env.example` for the exact shape. This is not stored anywhere by the migration itself (only the role/password exist in Postgres after `upgrade`) — you're responsible for saving the password you generated, same as any other credential.

## Creating a new migration

Filenames follow `YYYYMMDD_NNN_description.py` — date, then a counter that starts at `001` and resets each new day (not Alembic's default hash-based naming). This is set via an explicit `--rev-id` on every `alembic revision` call — `file_template` in `alembic.ini` can't express a per-day-resetting counter on its own.

```bash
# First migration of the day:
alembic revision --rev-id $(date +%Y%m%d)_001 -m "short_description"

# Second migration same day:
alembic revision --rev-id $(date +%Y%m%d)_002 -m "another_change"
```

Then edit the generated file's `upgrade()`/`downgrade()` functions, and run `alembic upgrade head` to apply it.

## Schema reference

Current tables (as of `20260805_001_create_document_graph.py`):

- **`documents`** — `doc_type` constrained to `recommendation | content | analysis | report`; `supersedes_id` self-references `documents.id` for version history (a doc chain, not just a timestamp).
- **`document_links`** — `from_doc_id` / `to_doc_id` / `relation` (free-text, e.g. `informed_by`, `supersedes`, `contradicts`, `references`) — the traversable graph structure between documents.
- **`run_log`** — one row per supervisor/subagent run: `agent`, `goal`, `summary`, optionally linked to the `document_id` it produced. The human-readable audit trail, distinct from the documents themselves. Since `20261016_007` it is the execution history's run record (claim, status, skills used, steps done); see [Data](../../architecture/data/data-model.md).

No `document_embeddings` table yet — semantic search over documents is deliberately deferred (see founding-decisions note) until document volume actually makes structural filtering (by `doc_type`, date, etc.) insufficient.

## Gateway quota ledger

Migration `20261011_001_gateway_quota_ledger.py` adds `gateway_quotas.reservations`, `gateway_quotas.cache` and the single-row `gateway_quotas.reservation_lock`. It also creates `horology_gateway`, a dedicated login without ownership, elevated attributes or access grants to document tables.

Before `alembic upgrade head`, save a strong `GATEWAY_DB_PASSWORD` in the private root `.env`. Use the existing direct owner DATABASE_URL for migrations. Runtime uses GATEWAY_DATABASE_URL in `mcp-servers/mcp-gateway/.env.local`: the existing pooled Neon host/database, with user horology_gateway and the new password (URL-encoded). Do not copy the document-graph owner credential into the gateway.

The runtime role cannot delete reservations, truncate tables or create objects in the quota schema. Reservations serialize through a transaction row lock before totals are checked. The downgrade drops quota data and the dedicated role; stop the gateway and back up accounting before any downgrade.

For local quota regression tests, use a disposable Postgres database, stamp its baseline as `20260807_001` and upgrade just the quota migration. This baseline stamp is for an empty test database only, never the deployed Neon database. Set GATEWAY_TEST_DATABASE_URL to the disposable admin connection and GATEWAY_TEST_RUNTIME_URL to its restricted gateway connection; tests truncate the test quota tables. Never point these test variables at Neon production data.
