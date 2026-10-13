# Implementation Note

## Topic
- fewer-database-round-trips

## Context
- Live checks with warm instances: gateway_status 1.3 s, list_documents 2.3 s (1.04 s in the tool), supabase_list_schema 5.1 s (3.7 s in the tool). Cloud Run is in us-central1, while Neon and Supabase are in Singapore, so each database round trip costs about 0.2 s.
- Moving the services to asia-southeast1 was considered and declined.

## Decision
- **Token cache.** After a token passes the database check, `GoogleOAuthProvider.load_access_token` keeps it in memory.
  - It is kept for up to 5 minutes (`OAUTH.access_cache_seconds`), never past the token's expiry, and is keyed by the SHA-256 of the token.
  - The cache holds at most 256 entries (`access_cache_size`); the least recently used is dropped first.
  - The account check (`check(email)`) still runs on every call.
  - `revoke_token` clears the grant's entries.
- **Login-default timeouts.** Alembic `20261014_001` stores `statement_timeout=10s` and `lock_timeout=3s` on `horology_gateway` and `horology_graph`. `Database.transaction()` no longer sends two `set_config` calls per transaction.
- **Supabase pool.** The gateway reuses metadata connections through a `psycopg_pool.ConnectionPool`:
  - at most 2 connections (`DATABASE.supabase_pool_size`);
  - each connection is read-only, set when it opens;
  - each is checked before use and dropped after 120 s idle;
  - each call still runs inside one transaction with its own 3 s `set_config` timeout.

## Rationale
- **Cache length.** 5 minutes, rather than 60 s, covers the gaps between an agent's tool calls. With one approved user, the longer revocation window is acceptable.
- **Why login defaults.** Passing the timeouts as connection startup options does not work through PgBouncer-style poolers, which reject unknown startup parameters. Role defaults are applied when each server session starts.
- **Verified on Neon.** Through the Neon pooler, the `horology_graph` login showed `SHOW statement_timeout` = 10s and `lock_timeout` = 3s on 2026-10-13. `tests/mcp_servers/test_login_timeouts.py` checks both logins in CI.
- **Timeouts are ceilings.** They don't hold connections. Waiting for a free pool connection is limited separately by `TIMEOUTS.database_connect` (5 s).
- **Why reuse is safe.** Reused Supabase connections carry no per-call state, and only fixed catalog queries run on them.

## Impact
- **Revocation lag.** A token revoked outside the process, for example with `scripts/revoke_email.py`, keeps working for up to 5 minutes. Deploying a new revision, or the service scaling to zero, clears the cache at once.
- **New login rule.** Any new service login must get the same role defaults in its migration.

## Follow-Ups
- Re-run `scripts/ops/live_check.py` after each deploy and compare with the baseline above.
