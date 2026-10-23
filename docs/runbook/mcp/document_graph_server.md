# Document graph MCP server (local)

Running, testing and connecting the local document-graph container. What it does and its tools: [document-graph architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/mcp/document-graph.md). Cloud deployment: [`../gcp/mcp_deployment.md`](../gcp/mcp_deployment.md).

The local copy has **no sign-in** and serves one workspace (`DOCUMENT_GRAPH_WORKSPACE`, default `welladino`). Its tools write documents and make paid embedding calls, so it must stay bound to `127.0.0.1`.

## Running it

It's its own Compose project, `horology-document-graph-mcp`, configured by the private `mcp-servers/document-graph/.env` (`DATABASE_URL_POOLED` with the `horology_graph` login, `OPENROUTER_API_KEY`). With Hermes connectivity (start Hermes first):

```bash
docker compose -f mcp-servers/document-graph/compose.yaml -f mcp-servers/document-graph/compose.hermes-network.yaml up -d --build
```

Without Hermes:

```bash
docker compose -f mcp-servers/document-graph/compose.yaml up -d --build
```

Logs:

```bash
docker compose -f mcp-servers/document-graph/compose.yaml logs document-graph-mcp
```

## Checking it's reachable only where intended

From the laptop (a 400 or 406 means it's up; it rejects a bare request without MCP headers):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/mcp
```

From inside Hermes:

```bash
docker exec horology-hermes curl -sS -o /dev/null -w "%{http_code}\n" http://document-graph-mcp:8765/mcp
```

The system tests check the exact `127.0.0.1` binding: [running tests](../testing/running_tests_and_audits.md).

## Connecting clients

For the current default Hermes agent, the `printf` answers "requires authentication?" (no) and "enable all tools?" (yes):

```bash
printf "n\ny\n" | docker exec -i horology-hermes hermes mcp add document-graph --url http://document-graph-mcp:8765/mcp
```

```bash
docker exec horology-hermes hermes mcp list
```

A laptop client such as Codex uses `http://127.0.0.1:8765/mcp`.

## Running the sync job locally

Complete an Application Default Credentials login with Sheets and read-only Drive scopes:

```bash
gcloud auth application-default login --scopes=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.readonly
gcloud auth application-default set-quota-project YOUR_GCP_PROJECT
```

The normal path reads workbook IDs from the active workspace row in Neon:

```bash
PYTHONPATH=mcp-servers/document-graph:jobs/document-graph-sync .venv/bin/dotenv -f mcp-servers/document-graph/.env run -- .venv/bin/python -m graph_sync
```

For a one-off local workspace, set `GRAPH_SYNC_WORKBOOKS` to a JSON map containing its `index`, `pipeline` and `decisions` spreadsheet IDs. Keep that value in the shell or another private configuration source; do not add live workbook IDs to documentation or Git.

Only Document Index rows with Graph Inclusion TRUE are imported. The job writes sync state back to the Sheet and embeds only new or changed revisions.

## Dependency pinning

`requirements.txt` pins exact versions. The MCP SDK's API has changed between versions before (`mcp` 2.0.0 has `mcp.server.mcpserver.MCPServer`, not `FastMCP`); read the release notes before bumping.
