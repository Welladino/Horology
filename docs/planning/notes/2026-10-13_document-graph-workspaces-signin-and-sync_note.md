# Document graph for subscription agents: workspaces, sign-in and the sheet sync

## Topic
- document-graph-workspaces-signin-and-sync

## Context

The operator wanted Claude and Codex agents, including cloud schedules, to search the document graph for what had already been done. Until then only local clients and project Owners could reach it. Options were weighed in the [research brief](../research/2026-10-13_document-graph-agent-access-and-sheet-sync_research.md); Hermes was out of scope.

## Decisions

**Plan (2026-10-13).** The document graph gets the gateway's Google sign-in as a second connector, rather than moving graph tools into the gateway; the shared code moves to `shared-runtime`. Each signed-in email maps to exactly one workspace; separate areas (Welladino, a full-time job) use separate copied workbooks. Agents keep `write_document`, tagged `source = agent`. The Document Index decides what sheet documents enter the graph through a TRUE/FALSE `Graph Inclusion`. An on-demand Cloud Run job fills the graph, started by an agent tool `sync_graph` limited to the caller's workspace; a sheet menu can come later. Starting a job through the Cloud Run Admin API avoids the identity-token audience problem a push from Apps Script would have. The job lives in `jobs/document-graph-sync/` and imports graph code but is never imported by the service; both ship in one image, deployed as the service and as the job with separate service accounts, and only the job's account can read Drive and write the workbook. This replaced the 2026-10-12 idea of reaching the graph through gateway adapters.

**Workspaces and Psycopg 3 (2026-10-13).** Migration `20261013_002` added required `workspace` and `source` and optional sheet identity (`index_document_id`, `drive_file_id`, `drive_url`, `source_revision`, `synced_at`); sheet rows must carry an Index ID and Drive file ID, unique per workspace. Existing rows became `welladino` / `agent`, and the defaults were then dropped so new rows must say both. `doc_type` widened to the Document Index's 12 types; downgrade deletes sheet rows and refuses if a new type is in use. The async pool moved into `shared-runtime/horology_runtime/database.py`; every query names its workspace, and links require both documents in the caller's workspace. `search_documents` was added; embedding runs outside database transactions; vectors are passed as text with a `::vector` cast to avoid a new dependency. In the live Document Index, `Graph Inclusion` became a TRUE/FALSE dropdown (all 15 rows FALSE), Graph Sync Status options were reduced to `not_applicable`, `pending`, `synced` and `error`, and Document Type gained `direction` and `pipeline`.

**Shared sign-in (2026-10-13).** The provider, consent page and token store moved (with history) into `shared-runtime/horology_runtime/oauth/`. Each service supplies its scope, an account check run at sign-in, consent and every token load and refresh, its consent wording, and its own token table. A token is refused unless its stored resource is that service's `/mcp`, added together with the separate tables because both services share one database. `DOCUMENT_GRAPH_WORKSPACES` maps approved emails to workspaces; an unmapped email can't finish sign-in or use a token. Migration `20261013_003` added the `horology_graph` login with narrow grants, so the public service no longer uses the owner login.

**Sync job (2026-10-13).** Credentials come from `google-auth`: application-default locally, the job's service account on Cloud Run. The Drive file `version` is the revision, so unchanged files aren't downloaded or re-embedded. Only Markdown, plain text and Google Docs are indexed, checked before download; the end-to-end test had shown a spreadsheet row being imported. CI switched to `pgvector/pgvector:0.8.0-pg16` and applies every migration from empty. 150 tests passed with none skipped, including cross-service token refusal and a full sync run as `horology_graph` (import, unchanged skip, supersedes link, spreadsheet error, removal on untick, other workspace untouched, status write-back).

**Deployed (2026-10-13).** The first cloud run found a real bug: a document was stored before it was embedded, so an OpenRouter failure left it unsearchable and later looked unchanged. Fixed in `c1d647b` with a test. Revisions, digests and the end-to-end run from Claude are in the [deployment runbook](../../runbook/gcp/mcp_deployment.md).

## Rationale

One sign-in implementation means a fix reaches both services; separate tables and resource-bound tokens mean neither accepts the other's credentials; and the sheet stays the operator's control over what enters the graph.

## Impact

- Accepted trade-off: the service image also carries the Google client libraries the service never uses; without Google credentials they can do nothing.
- Embeddings cost money only when a document's text changes.
- Later work added passage search ([note](2026-10-14_document-graph-passage-search_note.md)), topics and entities ([research](../research/2026-10-14_document-graph-topics-and-entities_research.md)). Current design: [document graph](../../architecture/mcp/document-graph.md).

## Follow-Ups

- A sheet menu that starts the same job.
