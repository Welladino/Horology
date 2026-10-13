# Implementation Note

## Topic
- document-graph-signin-and-sheet-sync

## Context
- Steps 2, 4 and 5 of the [document-graph plan](2026-10-13_document-graph-sheet-controlled-access_note.md): Google sign-in for document-graph, the Document Index sync job, and the `sync_graph` tool. Step 1 is in [workspaces and Psycopg 3](2026-10-13_document-graph-workspaces-psycopg3_note.md).

## Decision
- **Shared sign-in.** The OAuth provider, consent page, stylesheet and token store moved from the gateway into `shared-runtime/horology_runtime/oauth/` (with `git mv`, so history is kept). Each service now supplies:
  - its own scope (`gateway`, `graph`);
  - an account check that runs at sign-in, at consent and on every token load and refresh;
  - its own consent wording;
  - its own token table (`gateway_auth.records`, `graph_auth.records`).
- **Token changes in the shared provider:**
  - A token is refused unless its stored resource is that service's `/mcp`. Both services use the same Neon database, so this check was added at the same time as the separate tables.
  - Tokens now carry the verified email in `claims`.
  - The gateway's consent wording moved to `mcp-servers/mcp-gateway/shared/consent.py`.
- **Document-graph sign-in:** turned on with `DOCUMENT_GRAPH_OAUTH_ENABLED=true`. `DOCUMENT_GRAPH_WORKSPACES` maps each approved email to one workspace. An unmapped email can't finish sign-in or use a token. Local mode is unchanged: no sign-in, one workspace from `DOCUMENT_GRAPH_WORKSPACE`.
- **Migration `20261013_003`:**
  - Adds the `horology_graph` login, created from `GRAPH_DB_PASSWORD` the way the gateway login was.
  - Grants: SELECT/INSERT/UPDATE/DELETE on `documents`, SELECT/INSERT on `document_links`, SELECT/INSERT/UPDATE on `document_embeddings`, sequence usage, and full use of `graph_auth.records`.
  - Document-graph stops using the owner login once its secret is updated.
- **Sync job:** lives in `jobs/document-graph-sync/graph_sync` and runs as `python -m graph_sync` from the document-graph image.
  - Uses `google-auth` 2.61.0 for credentials: application-default locally, the job's service account on Cloud Run.
  - Revision identity is the Drive file `version`, so unchanged files are not downloaded or re-embedded.
  - Only Markdown, plain text and Google Docs are indexed. The file type is checked before anything is downloaded.
  - Embedding input is the title plus the first 8,000 characters.
- **`sync_graph` tool:** starts the job through the Cloud Run Admin API (`jobs:run`, overriding only `GRAPH_SYNC_WORKSPACE`). It accepts only a well-formed `GRAPH_SYNC_JOB` name and returns once the job has started.
- **CI:** Cloud Build now runs `pgvector/pgvector:0.8.0-pg16` and applies every migration from empty instead of stamping past the graph ones. It also passes `GRAPH_TEST_RUNTIME_URL` and audits the job's requirements.

## Rationale
- **Shared code:** one sign-in implementation, so fixes (such as the resource check) reach both services.
- **Separate tables and resource-bound tokens:** neither service accepts the other's credentials.
- **Restricted login before going public:** the owner login is not suitable for a public service.
- **Tests caught a real gap:** the file-type check now sits in the sync logic, because the end-to-end test showed a spreadsheet row being imported.

## Impact
- **Tests:** 150 passed and none skipped, run against a disposable pgvector Postgres (`horology-test-pg`) with all migrations applied from empty, plus a downgrade/upgrade of `002`/`003`.
  - New suites: sign-in (cross-service tokens refused, failed account checks block use and refresh, unknown token tables refused).
  - The sync job's end-to-end run as `horology_graph`: import, unchanged skip, supersedes link, error on a spreadsheet row, removal on untick, other workspace untouched, status write-back.
  - `sync_graph` request shape.
- **Images:** both build locally and pass `scripts/ci/check_image.py`.
- **Small deploy-window effect:** the shared advisory-lock key now includes the table name, so during a gateway deploy overlap the old and new revisions serialize on different keys.
- **Not done:** no Cloud Build, no deployment, no secrets or IAM changed. Migration `20261013_003` was applied to Neon on 2026-10-13 (password in the root `.env`); the local document-graph container now runs as `horology_graph` and `list_documents` works. The Sheets/Drive APIs are not enabled. The job has not run against the real sheet or Drive.

## Follow-Ups
- Run the [release steps](../../runbook/gcp/mcp_deployment.md#document-graph-sign-in-and-sheet-sync-release-prepared-2026-10-13-not-yet-run). Steps 5 and 12 need operator approval.
- Later: the sheet menu that starts the same job.
