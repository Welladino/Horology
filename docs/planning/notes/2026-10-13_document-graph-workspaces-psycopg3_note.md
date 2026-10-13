# Implementation Note

## Topic
- document-graph-workspaces-psycopg3

## Context
- Step 1 (with the tool part of step 3) of the [document-graph plan](2026-10-13_document-graph-sheet-controlled-access_note.md): workspaces and sheet identity in Neon, Psycopg 3, and search by meaning.

## Decision
- **Migration `20261013_002`:**
  - **`documents` gains columns:** `workspace` and `source` (`agent` or `sheet`) are required. `index_document_id`, `drive_file_id`, `drive_url`, `source_revision` and `synced_at` are optional.
  - **Sheet documents:** a `sheet` row must carry an Index ID and a Drive file ID. Workspace + Index ID is unique for sheet rows.
  - **Existing rows** become `welladino` / `agent`. The backfill defaults are then dropped, so new rows must state both values.
  - **`doc_type`** now accepts the 12 Document Index types from the sheet's Read Me tab.
  - **Downgrade** deletes sheet rows. It also fails if any row uses a new type, which is intended: there is no safe mapping back.
- **Psycopg 3, async:** the async pool moved from the gateway into `shared-runtime/horology_runtime/database.py`. The gateway's `Database` is now a subclass that adds its readiness check. Document-graph opens the pool in the server lifespan and passes it to the Neon client.
- **Workspace scoping:** every tool reads and writes only `current_workspace()`. For now that comes from `DOCUMENT_GRAPH_WORKSPACE` (default `welladino`); signed-in callers get their mapped workspace in step 2.
  - Links require both documents to be in the caller's workspace.
  - `write_document` tags `source = agent`.
- **New tool `search_documents(query, limit)`:** embeds the query and returns the nearest documents in the workspace with a similarity score (up to 20).
- **Embedding:** the OpenRouter call is now async and runs outside database transactions.
- **Layout, matching the gateway's `database/`:**
  - `document_graph/database/repositories/{documents,embeddings,links}.py` hold only parameterized SQL, and every query names its workspace.
  - `document_graph/graph.py` holds validation, workspace scoping and the embed-then-link steps. `link_similar` is reusable by the sync job.
  - `tools.py` only registers the tools.
  - `integrations/neon/` is removed; `integrations/openrouter/` stays.

## Rationale
- Moving the pool into `shared-runtime` now gives step 2's shared OAuth code a single database layer to build on.
- Passing vectors as pgvector text with an explicit `::vector` cast avoids a new dependency.

## Impact
- **Tests:** 112 passed, 14 skipped. The document-graph tests use a fake async database and cover workspace filters, search and the request shape. With Docker running, the Docker stack tests rebuilt and started the new image.
- **Verified live on 2026-10-13:**
  - The operator applied the migration to Neon. A read-only check shows `alembic_version` at `20261013_002`, the new columns present, and the 4 existing documents as `welladino` / `agent`.
  - The rebuilt local container listed all 8 tools.
  - `list_documents` and `list_unembedded_documents` succeeded against Neon.
  - `search_documents` was not called live, so no paid embedding was made.
- **Document Index sheet, edited 2026-10-13:**
  - `Graph Inclusion` is now a TRUE/FALSE table dropdown. All 15 rows were FALSE (previously 13 `pending_review` and 2 `exclude`).
  - `Graph Sync Status` options are now `not_applicable`, `pending`, `synced` and `error`. `needs_resync` was dropped because the sync compares Drive revisions itself.
  - The Read Me rows for Graph Inclusion, Graph Sync Status, Sync evidence, Graph mapping and Maintenance were updated.
  - The Document Type dropdown gained `direction` and `pipeline`, so it now matches the Read Me's 12 types and the graph's allowed list.

## Follow-Ups
- Step 2: shared OAuth and the email → workspace map.
