# Data

Horology keeps its own state in one Neon Postgres database. Business deliverables from subscription agents live in Drive and Sheets instead; Hermes' own session and kanban state stays in the gitignored `hermes-data/`.

![Neon schemas and logins](../diagrams/neon_data.svg)

## Logins

Each service connects through Neon's pooled endpoint with its own login, granted only what it needs. Migrations use the owner connection (`DATABASE_URL`), never a service login.

| Login | Used by | Can touch |
|---|---|---|
| `horology_graph` | Document-graph service and sync job | Graph tables in `public`, `graph_auth` |
| `horology_gateway` | Gateway | `gateway_quotas`, `gateway_auth`. It can add reservations but not delete or reset quota history. |
| `horology_cron_sweep_ro` | Unembedded-documents check (`scripts/check_unembedded_documents.py`) | SELECT on `documents` and `document_embeddings` |

## Schemas

| Schema | Tables | Purpose |
|---|---|---|
| `public` | `documents`, `document_links`, `document_embeddings`, `document_chunks` | Documents, links, document and section embeddings (pgvector, 768 dimensions) |
| `public` | `topics`, `section_topics` | Topic clusters and section membership |
| `public` | `entity_types`, `entities`, `entity_aliases`, `entity_mentions`, `entity_relations`, `relation_evidence`, `entity_decisions`, `entity_runs` | Entities, aliases, where they're mentioned, relationships and their evidence, review decisions, extraction runs |
| `public` | `graph_runs` | Sync and rebuild runs, one at a time per workspace |
| `public` | `run_log` | Reserved for Second-Soul's own audit trail; not used yet |
| `graph_auth` | `records` | Document-graph OAuth clients, codes and tokens (hashed) |
| `gateway_quotas` | `reservations`, `reservation_lock`, `cache` | Credit reservations, the lock that makes them atomic, one-hour response cache |
| `gateway_auth` | `records` | Gateway OAuth clients, codes and tokens (hashed) |

## Migrations

Root Alembic (`alembic/`, `alembic.ini`) owns every change; services never create tables at start-up. Revisions are named `YYYYMMDD_NNN_description` and run in order; the current head is `20261015_006` (`graph_runs`). Migrations that create logins read their passwords from the environment (for example `GATEWAY_DB_PASSWORD`), so passwords never enter the repository. Downgrading the gateway migrations destroys quota accounting. Workflow: [Alembic runbook](../../runbook/db/alembic_workflow.md).

Every driver is Psycopg 3: the services, the sync job, Alembic (`postgresql+psycopg`), CI and tests.
