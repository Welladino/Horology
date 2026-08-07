# Implementation Note

## Topic
- document-graph-embedding-sweep

## Context

Item 3 of `2026-08-07_document-graph-completeness-punch-list_note.md`: a daily check for documents missing an embedding (per `list_unembedded_documents`), escalating to an agent only when something is actually found, with no agent given code-execution capability to do it. The research brief (`2026-08-07_cron-script-security-pattern_research.md`) recommended a dedicated read-only Postgres role plus a Hermes cron `script` + `context_from` two-job chain. Implementation deviated from the `context_from` part of that plan once the real CLI/runtime was checked hands-on — this note captures what was actually built.

## Decision

**Read-only Postgres role** — `alembic/versions/20260807_001_add_readonly_role_for_cron_sweep.py`, run against the real Neon database. Creates `horology_cron_sweep_ro`, `GRANT SELECT` on exactly `documents` and `document_embeddings` — no `document_links`, no `run_log`, no default-privilege grant on future tables (a later migration adds those explicitly if ever needed). Verified hands-on, not just by reading the GRANT statement: connected as the new role and confirmed `SELECT` on both allowed tables succeeds, `INSERT` on `documents` is rejected (`InsufficientPrivilege`), and `SELECT` on `document_links` is rejected the same way.

**Sweep script** — `scripts/check_unembedded_documents.py`, synced to `/opt/data/scripts/` in the running container (same pattern as personas). Connects via `CRON_SWEEP_RO_DATABASE_URL` (the new role's own connection string — added to `docker-compose.yml`'s `hermes` service `environment:` block, `.env`, and `.env.example`), runs the same anti-join query as `list_unembedded_documents()`, and prints either `{"wakeAgent": false}` (nothing found) or a plain-text list of ids (found something).

Uses `asyncpg`, not `psycopg2` — checked what Hermes's own bundled Python interpreter (`/opt/hermes/.venv/bin/python3`, not this repo's `.venv`) actually has installed before assuming; `psycopg2` isn't there, `asyncpg` is.

**Single cron job, not two chained by `context_from`.** `hermes cron create --help` has `--script` and `--no-agent` but no `--context-from` flag; `context_from` turned out to be an agent-tool-only/JSON-editing feature for chaining two *separate* jobs' outputs, not something exposed to a plain `hermes cron create` call. A simpler, better-fitting mechanism exists instead: without `--no-agent`, a script's final stdout line of exactly `{"wakeAgent": false}` skips the agent for that run entirely (confirmed zero LLM turn); anything else wakes the agent with the script's full stdout (gate line included, not stripped) injected into its prompt. This gives the same "cheap on empty days, real agent turn only when needed" behavior in one job instead of two.

Verified hands-on end to end, not just per Hermes's own docs (which left the exact contract underspecified — no confirmation of whitespace tolerance, whether preceding stdout survives on the skip path, or whether the gate line itself gets stripped on the wake path):
- Deployed a throwaway probe script, created a real cron job pointing at it, triggered it via `hermes cron run <job_id>`.
- `wakeAgent: false` case: agent did not run; `hermes cron runs`/output file explicitly confirms "Script gate returned `wakeAgent=false` — agent skipped"; no preceding stdout surfaced anywhere.
- `wakeAgent: true` case: agent ran, correctly received and acted on a value the probe script printed, output file shows the full stdout (gate line included) injected verbatim under "## Script Output."
- Removed the probe job/script before creating the real one.
- Created the real job (`document-graph-embedding-sweep`, daily `0 9 * * *`, `--script check_unembedded_documents.py`), triggered it once via `hermes cron run` against the real, already-fully-embedded document graph (documents 5/6/7) — correctly returned `wakeAgent: false`, agent skipped, zero LLM cost. The "found something" path is mechanism-verified (via the probe) but not yet exercised with this specific script's real non-empty output, since fabricating an unembedded test document would pollute the real document graph — will be exercised naturally the first time a real document is actually missing an embedding.

## Rationale

Checked the actual CLI/runtime behavior before building against the research brief's `context_from` assumption, per this project's standing "verify hands-on" practice — the assumption (two jobs, `context_from` chaining) turned out to not match the real, exposed interface, and the actual mechanism found (`wakeAgent` gate, single job) is simpler than what was planned, not just a workaround. Using `asyncpg` over `psycopg2` for the same reason — checked what's actually importable in Hermes's bundled Python rather than assuming the MCP servers' dependency choices carry over to a completely different runtime.

## Impact

- New Postgres role in production Neon: `horology_cron_sweep_ro`.
- New files: `alembic/versions/20260807_001_add_readonly_role_for_cron_sweep.py`, `scripts/check_unembedded_documents.py`.
- `docker-compose.yml`: `hermes` service gained `CRON_SWEEP_RO_DATABASE_URL` in its `environment:` block (required, same `:?` pattern as other secrets).
- `.env` / `.env.example`: new `CRON_SWEEP_RO_DATABASE_URL` entry; also fixed a pre-existing formatting bug in `.env` (a missing newline between `GITHUB_TOKEN` and `GITHUB_REPO`, plus a duplicate `GITHUB_REPO` line) found while adding the new entry — unrelated to this work, fixed in passing since it was causing a dotenv parse warning.
- Real cron job created in the running Hermes instance: `document-graph-embedding-sweep`, id `2ba96135728f`, daily at 09:00 UTC.
- `docs/runbook/docker/hermes_setup.md` — new "Syncing cron scripts" section (mirrors the persona-sync section) plus a "Cron script runtime notes" subsection capturing everything verified hands-on here (Python interpreter path, dependency availability, secret-sanitization behavior, the `wakeAgent` contract) so the next script added to this project doesn't have to re-derive it.
- `docs/runbook/db/alembic_workflow.md` — new subsection on migrations needing extra env vars, using this migration as the example.

## Follow-Ups

- The "found something" path (real script output, real escalation, real `auto_link_similar_documents` calls from the agent) is unverified with live non-empty data — will happen naturally whenever a document actually ends up unembedded; worth a deliberate check the first time `hermes cron runs 2ba96135728f` shows a non-`wakeAgent=false` result, to confirm the agent's prompt (written into the job at creation time) actually gets it to call the right tool for each id correctly.
- No test coverage exists for `scripts/check_unembedded_documents.py` itself (it's a plain script, not part of either MCP server, and the existing `tests/mcp_servers/` pattern doesn't cover it) — low priority given how small and directly-verified it is, but worth a mocked unit test if it grows more logic later.
- Item 4 from the punch list (near-duplicate signaling in personas) is still open, unrelated to this note.
