# Document graph MCP server (local)

Running, testing and connecting the local document-graph container. What it does and its tools: [document-graph architecture](../../architecture/mcp/document-graph.md). Cloud deployment: [`../gcp/mcp_deployment.md`](../gcp/mcp_deployment.md).

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

Hermes, per profile (connections aren't shared between profiles). The `printf` answers "requires authentication?" (no) and "enable all tools?" (yes):

```bash
printf "n\ny\n" | docker exec -i horology-hermes hermes mcp add document-graph --url http://document-graph-mcp:8765/mcp
```

```bash
docker exec horology-hermes hermes mcp list
```

A laptop client such as Codex uses `http://127.0.0.1:8765/mcp`.

## Running the sync job locally

See the [document-graph README](../../../mcp-servers/document-graph/README.md#sign-in-and-the-document-index-sync).

## Dependency pinning

`requirements.txt` pins exact versions. The MCP SDK's API has changed between versions before (`mcp` 2.0.0 has `mcp.server.mcpserver.MCPServer`, not `FastMCP`); read the release notes before bumping.
