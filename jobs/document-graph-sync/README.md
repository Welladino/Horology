# Document graph sheet sync

On-demand job that copies Document Index rows marked `Graph Inclusion = TRUE` into the document graph, for one workspace or every configured workbook.

- `graph_sync/index.py`: reads Document Index rows; no network or database.
- `graph_sync/google.py`: Sheets read/write-back and Drive downloads with the job's Google credentials.
- `graph_sync/sync.py`: one workspace's pass. Imports or refreshes TRUE rows when their Drive `version` changed, embeds only changed text (title plus the first 8,000 characters), links similar documents and `Supersedes document ID`, removes sheet documents now FALSE or gone, and writes Graph Sync Status, Graph Document ID and Last Synced Revision back.
- `graph_sync/__main__.py`: `python -m graph_sync`.

It imports `document_graph` (repositories, embeddings, linking) and never the reverse. It ships inside the document-graph image and runs as the Cloud Run job `document-graph-sync`; the `sync_graph` MCP tool starts it for the caller's workspace.

| Variable | Meaning |
| --- | --- |
| `GRAPH_SYNC_WORKBOOKS` | JSON map, workspace → Document Index spreadsheet id |
| `GRAPH_SYNC_WORKSPACE` | Optional: sync only this workspace (set by `sync_graph`) |
| `DATABASE_URL_POOLED` | Neon pooled URL with the `horology_graph` login |
| `OPENROUTER_API_KEY` | Embeddings |

Indexable files: Markdown or plain-text uploads (up to 2 MB) and Google Docs. Other types get `error` in Graph Sync Status. A file Drive won't show the job's identity (403/404, usually because its folder isn't shared with `document-graph-sync@horology-dev.iam.gserviceaccount.com`) gets `not_shared`; share the folder as Viewer and sync again. A row that errors keeps its previous graph copy. Agent-written documents (`source = agent`) are never touched.

Run it locally: [document-graph README](../../mcp-servers/document-graph/README.md#sign-in-and-the-document-index-sync). Cloud setup: [deployment runbook](../../docs/runbook/gcp/mcp_deployment.md). Tests: `tests/jobs/`.
