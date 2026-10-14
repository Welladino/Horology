# Document graph MCP

Separate Neon document graph and OpenRouter embeddings service.

- `server.py`: MCP entrypoint.
- `document_graph/tools.py`: registers the fixed document tools, including `search_documents` (passage search by meaning). Every tool is scoped to one workspace (`document_graph/shared/workspace.py`).
- `document_graph/graph.py`: the tools themselves. Each validates input, takes the caller's workspace and calls a [`graph_core`](../../document-graph-core/README.md) service; there's no graph logic or SQL here.
- `sync_graph` and `rebuild_topics` start the sync job through `graph_core.runs` (shared with the job, which starts its own follow-up runs). They refuse while a run is in progress for the workspace, or when the same run was asked for in the last 5 minutes.
- `requirements.txt`: pinned dependencies for this service, `graph_core` and the job.

Graph logic (documents, sections, embeddings, linking, search) lives in `document-graph-core/`, shared with the sync job. Neither this service nor the job imports the other.

Copy `.env.example` to `.env` for a new setup. Required: DATABASE_URL_POOLED (Neon pooled connection) and OPENROUTER_API_KEY (embeddings). Optional: EMBED_MODEL, default google/gemini-embedding-001, DOCUMENT_GRAPH_BIND, default 0.0.0.0, and DOCUMENT_GRAPH_WORKSPACE, default welladino (the one workspace local, unauthenticated clients see). Embeddings remain 768-dimensional to match the database. DATABASE_URL is not an environment input; no duplicate connection string is needed. The document-graph Compose project loads the service-specific .env; Python does not load it itself. Keep .env excluded from Git and images. Root credentials still required by other components should remain there.

0.0.0.0 binds the container listener to its network interfaces, not to a chosen remote server. Compose publishes this service only at `127.0.0.1:8765`; laptop clients use `http://127.0.0.1:8765/mcp`. Hermes reaches it by Docker service name, http://document-graph-mcp:8765/mcp. Binding to 127.0.0.1 inside the container would prevent other containers connecting. No application authentication is implemented here; do not expose this service publicly before adding cloud authentication and embedding limits.

Application operation logs emit JSON to stdout with tool, integration, duration, outcome and correlation ID. Tool errors expose only a category and request ID; arguments, documents, credentials and raw exception messages are excluded. Neon has a five-second connection timeout, ten-second statement timeout and three-second lock timeout. OpenRouter retains its thirty-second HTTP timeout. No automatic retries. Inspect locally with `docker compose -f mcp-servers/document-graph/compose.yaml logs document-graph-mcp`.

Timeout settings and logging/error handling are imported from the common package at `../../shared-runtime/horology_runtime/`. Change `settings.py` or `operations.py` there and rebuild both images. Native development requires installing the shared runtime as described in its README. Docker build context is the repository root, using its secret-safe `.dockerignore`; use the documented Compose commands.

## Independent local Compose project

Document-graph runs in the `horology-document-graph-mcp` project, separately from Hermes and the gateway. Use `compose.yaml` alone for its private standalone network, or combine it with `compose.hermes-network.yaml` to attach to the existing `horology_default` network as `document-graph-mcp`. Start Hermes first when using that overlay. Only localhost port 8765 is published. See [running services](../../docs/runbook/docker/running_all_services.md) for commands.

## Local Codex connection

Use `http://127.0.0.1:8765/mcp` for Codex on your laptop. `document-graph-mcp` is a Docker network hostname, so it is used by Hermes rather than host applications. The local document-graph endpoint has no application OAuth; its tools include document writes and paid embeddings. Keep the host binding at `127.0.0.1`. Cloud Run remains protected by IAM.

## Sign-in and the Document Index sync

With `DOCUMENT_GRAPH_OAUTH_ENABLED=true` the server uses the shared Google sign-in (`horology_runtime.oauth`) with its own `graph_auth.records` table, scope `graph`, and `DOCUMENT_GRAPH_WORKSPACES` mapping each approved email to one workspace. Local Compose leaves it off. Cloud steps: [deployment runbook](../../docs/runbook/gcp/mcp_deployment.md#document-graph-sign-in-and-sheet-sync-release-prepared-2026-10-13-not-yet-run).

`sync_graph` starts the Cloud Run job named in `GRAPH_SYNC_JOB` for the caller's workspace. The job code lives in [`jobs/document-graph-sync/`](../../jobs/document-graph-sync/) and ships in this image (`python -m graph_sync`).

Run the sync locally against Neon, as yourself. One-time Google login with the Sheets and Drive scopes (quota is charged to `horology-dev`, where both APIs must be enabled):

```bash
gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.readonly
```

```bash
gcloud auth application-default set-quota-project horology-dev
```

Then, from the repository root. `dotenv` loads this folder's `.env` (Neon via `horology_graph`, OpenRouter); the shell can't source that file because its URLs contain `&`:

```bash
GRAPH_SYNC_WORKBOOKS='{"welladino":"1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc"}' PYTHONPATH=mcp-servers/document-graph:jobs/document-graph-sync .venv/bin/dotenv -f mcp-servers/document-graph/.env run -- .venv/bin/python -m graph_sync
```

It prints one summary line per workspace and writes status back to the sheet. Only rows with Graph Inclusion TRUE are imported; embeddings are made only for changed files.
