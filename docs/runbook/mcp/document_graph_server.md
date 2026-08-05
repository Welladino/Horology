# Document Graph MCP Server

A small, purpose-built MCP server exposing exactly four operations against the document graph (Neon Postgres: `documents` / `document_links` / `run_log`) — no arbitrary SQL, no schema access beyond these four tools. This is deliberately narrower than Neon's own official MCP server (`neondatabase/mcp-server-neon`), which is a general database-admin tool (arbitrary SQL, branch management, migrations) — too broad a capability to hand an autonomous agent. See [`docs/planning/notes/2026-08-06_document-graph-mcp-server_note.md`](../../planning/notes/2026-08-06_document-graph-mcp-server_note.md) for the full rationale.

## What it exposes

- `write_document(doc_type, title, content, created_by_agent, supersedes_id?)` — `doc_type` constrained to `recommendation | content | analysis | report`.
- `link_documents(from_doc_id, to_doc_id, relation)` — free-text `relation`; duplicate edges are silently ignored.
- `get_document(id)` — full content of one document.
- `list_documents(doc_type?, limit?)` — metadata only (no content), most recent first.

The Neon connection string (`DATABASE_URL_POOLED`) lives only in this container's own environment — never in Hermes's environment, never visible to whatever calls these tools.

## Running it

It's a service in `docker-compose.yml` (`document-graph-mcp`), built from `mcp-servers/document-graph/`. It idles (`sleep infinity`) rather than running as a standalone daemon — the actual MCP server process is invoked per-connection via `docker exec`, matching how `hermes mcp serve` itself works (stdio transport, no exposed port).

```bash
# Build + start (idling, ready for exec)
docker compose up -d document-graph-mcp

# Rebuild after changing server.py or requirements.txt
docker compose build document-graph-mcp
docker compose up -d document-graph-mcp
```

## Testing it directly (without a real MCP client)

The server speaks JSON-RPC over stdio. You can hand-test it, but a heredoc that closes stdin immediately after the last line will kill the process before an async tool-call response is flushed back — use a persistent stdin (e.g. a subshell with a trailing `sleep`) instead:

```bash
(
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0"}}}'
echo '{"jsonrpc": "2.0", "method": "notifications/initialized"}'
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}'
sleep 2
) | docker exec -i horology-document-graph-mcp python server.py
```

Known gotcha found during setup: if stdin closes before the response is flushed, the tool call can still have executed server-side (e.g. a `write_document` call that appears to "hang" may have already committed the row) — don't assume a missing response means nothing happened. Check the DB directly if unsure.

## Connecting Hermes to it

Not yet wired up. Planned: register it as an MCP server Hermes can call via `hermes mcp add`, using `docker exec -i horology-document-graph-mcp python server.py` as the command (same stdio-subprocess pattern as the Claude-to-Hermes bridge documented in the founding-decisions and subagent-design notes).

## Dependency pinning

`requirements.txt` pins exact versions (`mcp==2.0.0`, not `>=`). The MCP Python SDK's API changed between versions during this project's own build — `FastMCP` (the class name assumed from prior knowledge) doesn't exist in `2.0.0`; the current class is `mcp.server.mcpserver.MCPServer`, same constructor/decorator/`run()` shape otherwise. Verify against the SDK's release notes before bumping the version.
