# Implementation Note

## Topic
- document-graph-sheet-controlled-access

## Context
- The operator wants Claude and Codex agents, including cloud schedules, to search the document graph for what has already been done. Today only local clients and project Owners can reach it. Investigation: [research brief](../research/2026-10-13_document-graph-agent-access-and-sheet-sync_research.md).
- Hermes is out of scope for now.

## Decision
Decided on 2026-10-13; not implemented yet:
- **Sign-in:** document-graph gets the gateway's Google OAuth + Audience sign-in as a second connector. The shared code moves into `shared-runtime`.
- **Workspaces:** each signed-in email maps to exactly one workspace. Separate areas (Welladino, full-time job) use separate copied workbooks. The workspace id is the Document Index `Workspace` value.
- **Agent writes:** agents keep `write_document` and the existing tools, tagged `source = agent` in their own workspace.
- **Search:** add `search_documents(query)`.
- **Sheet control:** the Document Index decides what sheet documents enter the graph, using `Graph Inclusion` as a TRUE/FALSE dropdown.
- **Sync:** an on-demand Cloud Run Job (`document_graph.sync`) fills the graph. There's no hourly schedule.
- **Starting the sync:** the job is started first by an agent tool, `sync_graph`, limited to the caller's workspace. A sheet menu comes later.

- **Code layout:** the sync job lives in its own folder, `jobs/document-graph-sync/` (package `graph_sync`), holding only the Google Sheets/Drive code and the sync steps. It imports the graph's Neon, embedding and linking code from `document_graph`. Imports only go that way: `document_graph` never imports `graph_sync`, and `sync_graph` just asks the Cloud Run API to start the job.
- **One image, two uses:** the document-graph Dockerfile copies both folders into `/app` and installs both requirements files. It is deployed as the Cloud Run service (`python server.py`) and as the Cloud Run job (`python -m graph_sync`), each with its own service account. Only the job's account gets access to the workbook and Drive folder.

- **Two connectors:** the operator preferred them over moving the graph tools into the gateway. Reusing the shared sign-in avoids a second implementation.
- **Job instead of a push:** starting a job uses the Cloud Run Admin API, which avoids the identity-token audience problem a direct push from Apps Script would have.
- **Agent trigger first:** it reuses the sign-in the read tools need anyway. The sheet menu needs an Apps Script project link and an extra scope that are still unverified.

## Impact
- **Neon:** a migration adds workspace, source and sheet identity fields to `documents`. Existing rows become `welladino` / `agent`.
- **Live sheet:** the `Graph Inclusion` dropdown changes from its current values (`pending_review`) to TRUE/FALSE. No sheet change has been made yet.
- **Cloud:** the document-graph Cloud Run service turns off its invoker IAM check once OAuth is in place, which needs separate operator approval. A new job and service account get Editor on the workbook (for status write-back) and Viewer on the output folder.
- **Accepted trade-off:** the MCP service's image also contains the Google client libraries, though the service never uses them. Without Google credentials they can't do anything. The same folders can build two image variants later if wanted.
- **Cost:** embeddings go to OpenRouter, so they're only made when a document's text changes.

## Follow-Ups
- Resolved 2026-10-13:
  - the job writes sync status back to the sheet, so its service account gets Editor on the workbook
  - `doc_type` is widened to the Index's Document Type values
  - document-graph moves to Psycopg 3
- Still open: which APIs to enable, and whether `sync_graph` waits for the job.
- Then build steps 1–6 from its recommendation, with a note per step.
- This note supersedes the 2026-10-12 brief's suggestion to reach the graph through gateway adapters.
