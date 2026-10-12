# Async gateway database repositories

## Decision and implementation

Move the gateway's Neon persistence from blocking Psycopg 2 calls into `database/connection.py` and `database/repositories/{quotas,cache,oauth}.py`. Use pinned Psycopg 3.3.6 and psycopg-pool 3.3.3. The HTTP application lifespan owns a four-connection maximum async pool on the serving event loop, including OAuth HTTP routes. Prepared statements are disabled for transaction-pool compatibility; certifi/verify-full Neon trust is preserved.

Quota coordinator row locks and OAuth advisory transaction locks keep checks/consumption/issuance atomic. Queries remain parameterized; schema/history/permission grants are unchanged by this driver refactor. Exceptions and cancellation roll back transactions. Shared settings hold timeouts and pool size; shared error categories recognize the new driver's failures. The Dockerfile and source/image allowlists include the database package.

Removed the old shared ledger/OAuth storage modules and updated consumers to await repository operations. Supabase metadata, document-graph and Alembic drivers remain unchanged.

## Verification

106 local tests passed with a disposable PostgreSQL 16 container and the restricted horology_gateway role. Coverage includes concurrent credit reservation across independent pools, preserved totals after reopening a pool, cache isolation/expiry, code single consumption, credential hashing, refresh/revocation serialization, wrong-client rollback, cancellation rollback, lifecycle cleanup and denied quota deletion/DDL. Gateway dependency audit reports no known vulnerabilities. Local HTTP MCP smoke passed with thirteen tools, authentication and parked-tool denials, without provider calls.

The Hermes/document-graph Docker-stack suite was excluded: it would build/start unrelated services using real credentials. No Cloud Build, production migration, deployment, commit or push was performed. The disposable database is removed after verification.
