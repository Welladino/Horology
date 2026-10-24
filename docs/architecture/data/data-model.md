# Data model

Horology keeps its own state in one Neon Postgres database. Business deliverables from subscription agents live in Drive and Sheets instead; Hermes' private sessions and runtime state stay in Watchmaker's ignored `runtime/hermes-data/`. See [Workspace data flow](workspace-data-flow.md) for when agent runs, Sheet changes and documents reach Neon, and [MCP request and database flow](mcp-request-flow.md) for identity, tool calls and quota records.

```mermaid
flowchart TB
  db["<b>One Neon database</b><br/>Alembic in alembic/versions owns every schema change, run with the owner connection"]
  subgraph graphdb["Document graph · login horology_graph"]
    docs[("<b>Documents</b><br/>documents (workspace, source, domain, pipeline_id), document_links, document_embeddings, document_chunks")]
    topics[("<b>Topics</b><br/>topics, section_topics")]
    entities[("<b>Entities</b><br/>entity_types, entities, entity_aliases, entity_mentions, entity_relations, relation_evidence, entity_decisions, entity_runs")]
    runs[("<b>Runs</b><br/>graph_runs: one sync or rebuild per workspace at a time. run_log, run_outputs and Pipeline copies with their change events: the execution history")]
    gauth[("<b>graph_auth</b><br/>records: OAuth clients, codes and tokens, hashed")]
  end
  subgraph gateway["Gateway · login horology_gateway"]
    quotas[("<b>gateway_quotas</b><br/>reservations, reservation_lock, cache: daily and monthly credits, one-hour cache")]
    gwauth[("<b>gateway_auth</b><br/>records: OAuth clients, codes and tokens, hashed")]
  end
  sweep["<b>horology_cron_sweep_ro</b><br/>Read-only login for the unembedded-documents check: SELECT on documents and document_embeddings"]
  db --> graphdb
  db --> gateway
  sweep -. reads .-> docs
```

## Logins

Each service connects through Neon's pooled endpoint with its own login, granted only what it needs. Migrations use the owner connection (`DATABASE_URL`), never a service login.

| Login | Used by | Can touch |
|---|---|---|
| `horology_graph` | Document-graph service and sync job | Graph tables in `public`, `graph_auth`; read-only on `access` |
| `horology_gateway` | Gateway | `gateway_quotas`, `gateway_auth`, read-only on `access`. It can add reservations but not delete or reset quota history. |
| `horology_cron_sweep_ro` | Watchmaker's unembedded-documents check | SELECT on `documents` and `document_embeddings` |

## Schemas

| Schema | Tables | Purpose |
|---|---|---|
| `public` | `documents`, `document_links`, `document_embeddings`, `document_chunks` | Documents, links, document and section embeddings (pgvector, 768 dimensions) |
| `public` | `topics`, `section_topics` | Topic clusters and section membership |
| `public` | `entity_types`, `entities`, `entity_aliases`, `entity_mentions`, `entity_relations`, `relation_evidence`, `entity_decisions`, `entity_runs` | Entities, aliases, where they're mentioned, relationships and their evidence, review decisions, extraction runs |
| `public` | `graph_runs` | Sync and rebuild runs, one at a time per workspace |
| `public` | `run_log`, `run_outputs` | Execution history: one row per agent run (claim, status, self-reported skills, steps and notes) and the outputs linked to it. The service login can't delete runs. |
| `public` | `pipeline_items`, `pipeline_events`, `decisions`, `document_index` | Copies of Pipeline Master, the Decision Register and the Document Index, kept by the sync job's records pass, and every field change between copies (attributed to the run active at the time) |
| `access` | `mcp_servers`, `workspaces`, `users`, `workspace_members`, `user_mcp_access`, `workspace_pages` | Who may use which MCP server and workspace, each workspace's spreadsheets and its optional private Pages mapping. Service logins have read-only access where needed; owner-run scripts change the records. |
| `graph_auth` | `records` | Document-graph OAuth clients, codes and tokens (hashed) |
| `gateway_quotas` | `reservations`, `reservation_lock`, `cache` | Credit reservations, the lock that makes them atomic, one-hour response cache |
| `gateway_auth` | `records` | Gateway OAuth clients, codes and tokens (hashed) |

## Migrations

Root Alembic (`alembic/`, `alembic.ini`) owns every change; services never create tables at start-up. Revisions are named `YYYYMMDD_NNN_description` and run in order; the source head is `20261022_009` (workspace Pages mappings), which must be applied before deploying the updated gateway. Migrations that create logins read their passwords from the environment (for example `GATEWAY_DB_PASSWORD`), so passwords never enter the repository. Downgrading the gateway migrations destroys quota accounting. Workflow: [Alembic runbook](https://github.com/Welladino/Horology/blob/main/docs/runbook/db/alembic_workflow.md).

Every driver is Psycopg 3: the services, the sync job, Alembic (`postgresql+psycopg`), CI and tests.
