# Neon gateway quota ledger

## Topic
- neon-gateway-quota-ledger

## Context
- Implement the persistent accounting prerequisite from the GCP deployment plan, using existing Neon and Alembic.

## Decision
- Replace the gateway local ledger completely with the Postgres adapter at shared/ledger.py. Migration 20261011_001 adds a dedicated gateway_quotas schema, reservations/cache tables and a transaction coordinator row. It provisions horology_gateway with narrowly scoped grants.
- All quota reservations take a transaction row lock before reading totals and inserting usage. Existing budget, per-tool and per-provider assignment limits remain; failed upstream calls retain reservations.
- Runtime uses GATEWAY_DATABASE_URL in private .env.local; migration uses root DATABASE_URL and GATEWAY_DB_PASSWORD. Shared database timeout policy is reused with SET LOCAL for pooled connections.

## Rationale
- Accounting survives container restarts and serializes across instances using the existing database. No new cloud database service is needed.

## Impact
- Removed the gateway state volume, ledger file paths and runtime table creation. Preserved 14 existing reservations and two cache entries in the cutover. The temporary private backup was retained until verification and then removed.
- Historical notes still describe previous decisions. Hermes upstream session storage is separate from the removed gateway accounting and is not changed by this migration.

## Follow-Ups
- Continue Cloud Run configuration, secrets and authentication according to the deployment plan.
- Runtime assignments still expire and need provisioning for scheduled runs; this migration does not implement OAuth or schedules.

## Verification
- 52 repository/gateway tests passed, including concurrent accounting, restart counts, previous-period budgets, restricted-role permissions, failure without fallback and separate Neon TLS trust. Quota tests ran only on disposable local Postgres.
- Applied revision 20261011_001 to Neon; imported all 14 prior reservations and two cache entries. Confirmed the gateway login cannot SELECT public application tables.
- Built and restarted the gateway image; real MCP handshake, 17 tools, rejected invalid authentication and scope-denial checks passed without paid provider calls.
- Deleted the obsolete gateway state volume and private temporary cutover files after verification. Changes are not committed or pushed.
