# Research Brief

## Topic
- document-graph-agent-access-and-sheet-sync

## Question
- How can Claude and Codex agents (local and cloud) use the document-graph MCP to find what has already been done, with the Document Index sheet deciding which Drive documents enter the graph, and with Welladino and other workspaces (for example a full-time job) kept apart?
- Hermes is out of scope for now.

## Summary
- Today the document graph is reachable only locally (`localhost:8765`, no sign-in) or by project Owners holding a one-hour Google identity token. Claude, ChatGPT and Codex cloud connectors cannot use it.
- Recommended: give document-graph the gateway's Google OAuth + Audience sign-in (second connector), add workspaces and a `source` marker to the Neon documents, add `search_documents(query)`, and fill the graph from the Document Index through an on-demand Cloud Run Job started by an agent tool (`sync_graph`). A sheet menu that starts the same job comes later.
- The live Document Index already has `Workspace`, `Graph Inclusion`, `Graph Sync Status`, `Graph Document ID` and `Last Synced Revision` columns; the design reuses them instead of adding a new `Graph` column.

## Sources
- `mcp-servers/document-graph/server.py`, `document_graph/tools.py`, `document_graph/integrations/neon/client.py`, `document_graph/integrations/openrouter/client.py`.
- `alembic/versions/20260805_001_create_document_graph.py`, `20260806_001_add_document_embeddings.py`.
- `mcp-servers/mcp-gateway/shared/oauth/`, `mcp-servers/mcp-gateway/database/repositories/oauth.py` (sign-in to reuse).
- Live Cloud Run settings for `document-graph`, read with `gcloud --configuration=horology-view` on 2026-10-13: URL `https://document-graph-wjk34wbhza-uc.a.run.app`, ingress `all`, invoker IAM check on, no `roles/run.invoker` binding.
- Live `Welladino — Document Index` headers, read 2026-10-13.
- Earlier proposal: [MCP next steps](2026-10-12_mcp-next-steps_research.md) (graph access through gateway adapters; Graph inclusion fields).

## Findings

### What the document-graph MCP does today
| Tool | Behaviour |
|---|---|
| `write_document` | Stores type, title, full content, `created_by_agent`, optional `supersedes_id` |
| `link_documents` | Adds a named edge between two documents |
| `get_document` | One document by id, with content |
| `list_documents` | Newest first, optional type filter, up to 100 |
| `get_related_documents` | Every document linked to or from one document |
| `list_unembedded_documents` | Documents without an embedding |
| `auto_link_similar_documents` | Embeds one document (OpenRouter, `google/gemini-embedding-001`, 768 dimensions), compares with all others, adds `related_to` above 0.85 |

Gaps for agent use:
- No search by meaning: similarity only runs from one stored document to the rest, so an agent cannot ask "what have we done on pricing?".
- Agents write directly; nothing ties graph content to the Document Index.
- No workspace: every caller sees every document.
- No Drive file identity, Document Index ID or revision on a document, so re-indexing cannot be idempotent (also noted in the 2026-10-12 brief).
- No application sign-in; the server docstring says cloud authentication is deferred.

### How it can be reached today
- Local: start the stack ([running_all_services.md](../../runbook/docker/running_all_services.md)), then `claude mcp add --transport http document-graph http://localhost:8765/mcp` or `codex mcp add document-graph --url http://localhost:8765/mcp`. Local clients only, while the Mac is on.
- Cloud: Cloud Run checks every request for a Google identity token for that service URL from an identity with Cloud Run Invoker. Nobody holds that grant, so in practice only project Owners can call it, with a token from `gcloud auth print-identity-token`. Codex could pass such a header, but the token expires hourly; not usable for schedules.

### Sign-in options
1. Serve the read tools from the gateway (one connector). Rejected by the operator in favour of keeping two connectors.
2. Give document-graph the gateway's Google OAuth + Audience sign-in (chosen). Move `shared/oauth/` and the OAuth repository into `shared-runtime` so both services use one copy. The gateway code is async (Psycopg 3) and document-graph is sync (Psycopg 2), so the shared code needs an adapter or document-graph moves to Psycopg 3. Needs a second callback URL on the Google OAuth client and the invoker IAM check turned off on document-graph (same pattern the operator approved for the gateway on 2026-10-11; needs its own approval).

### Workspaces
- One person runs separate workspaces (Welladino, full-time job) in separate copied workbooks, never one sheet.
- The Document Index `Workspace` column already holds `welladino`; use that value as the workspace id rather than the workbook id, because it is human-readable and already populated.
- Each signed-in Google email maps to exactly one workspace (operator decision). Every read tool filters by it, and `sync_graph` only syncs the caller's workspace.
- Employer-policy caution for a job workspace: titles, links and text would be copied into a personal Neon and sent to OpenRouter for embeddings.

### Writing into the graph
- Agents keep `write_document` and the other tools, tagged `source = agent`, and written into their own workspace (operator decision).
- Documents from the sheet are tagged `source = sheet` and keyed by workspace + Document Index ID.
- Writing a document to Drive does not create an Index row; the agent adds the row because the workflow skills say so. Apps Script only syncs to ClickUp.
- `Graph Inclusion` currently holds `pending_review`. The operator wants a TRUE/FALSE dropdown; proposal: change that column's dropdown to TRUE/FALSE (existing `pending_review` → FALSE) rather than adding a separate `Graph` column.

### Sync trigger
| Option | Verdict |
|---|---|
| Hourly Cloud Scheduler | Not wanted; operator prefers on demand |
| Apps Script pushing to the private service | Apps Script's Google identity token is issued for its OAuth client, not the Cloud Run service URL; needs custom audiences or a separate secret. Unverified |
| Cloud Run Job, started on demand (chosen) | Same image, `python -m document_graph.sync`. Starting a job goes through the Cloud Run Admin API, so no service sign-in is needed |

Ways to start the job:
1. Agent tool `sync_graph` on document-graph (first). The document-graph runtime identity needs permission to run that one job only.
2. Terminal: `gcloud run jobs execute document-graph-sync --region us-central1` (free, for testing).
3. Sheet menu "Horology → Sync graph now" (later). Apps Script calls the Cloud Run Admin API with the user's OAuth token; needs the `cloud-platform` scope and the script linked to the `horology-dev` project. Unverified.

### What the job does per run
1. Read the workspace's Document Index through the Sheets API.
2. For `Graph Inclusion = TRUE` rows: fetch the file through the Drive API. Indexed files are `.md` uploads (download content), and Google Docs would need export as text, so handle both. Skip unchanged files (Drive revision or modified time compared with the stored revision). Store or update, embed, link `Supersedes document ID`, run similarity linking.
3. Remove `source = sheet` documents whose row is now FALSE or gone. Exclusion stops serving immediately.
4. Access: the job's service account is shared as Viewer on the workbook and on the workspace's Drive output folder (folder share covers its files). Writing status back to `Graph Sync Status`, `Graph Document ID` and `Last Synced Revision` would need Editor on the workbook.

### Code layout (decided 2026-10-13)
- `jobs/document-graph-sync/graph_sync/` holds Sheets/Drive access and the sync steps; it imports `document_graph` for Neon, embeddings and linking, never the reverse.
- Same image as the MCP: the Dockerfile copies both into `/app` and installs both requirements files. The service runs `python server.py`; the job runs `python -m graph_sync`.
- Knock-on changes: allowlist the folder in `.dockerignore` and `.gcloudignore`, add tests under `tests/jobs/`, and check `graph_sync` imports in `scripts/ci/check_image.py`.

### Neon schema changes (proposal)
- `documents`: add `workspace`, `source` (`agent` | `sheet`), `index_document_id`, `drive_file_id`, `drive_url`, `source_revision`, `synced_at`. Unique on (`workspace`, `index_document_id`) where `source = sheet`.
- Existing rows: `workspace = welladino`, `source = agent`.
- Let `doc_type` accept the Index's `Document Type` values (for example `plan`), or map them; today it allows only `recommendation`, `content`, `analysis`, `report`.

## Recommendation
Status 2026-10-13: steps 1–5 built and tested locally; step 6 is written up in the deployment runbook and not run.

Build in this order, each step testable alone:
1. Neon migration: workspace, source and sheet identity fields; backfill existing rows.
2. Move OAuth into `shared-runtime`; add it to document-graph with an email → workspace map.
3. Workspace-filtered tools; `write_document` tags `source = agent`; add `search_documents(query)`.
4. `document_graph.sync` job.
5. `sync_graph` tool that starts the job for the caller's workspace.
6. Deploy: job + service account shares, callback URL, invoker check off (operator approval).
7. Later: sheet menu.

## Open Questions
- Resolved 2026-10-13: the job writes status back to `Graph Sync Status`, `Graph Document ID` and `Last Synced Revision` (service account gets Editor on the workbook); widen `doc_type` to accept the Index's Document Type values; move document-graph to Psycopg 3.
- APIs to enable in `horology-dev`: Sheets API, Drive API (Cloud Run Admin is already on).
- How long a job takes to start on demand; whether `sync_graph` should wait for the result or return "started".
- Whether the Apps Script → Cloud Run Admin API call works with a linked project (test before building the sheet menu).
