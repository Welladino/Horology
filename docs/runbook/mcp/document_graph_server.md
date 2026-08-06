# Document Graph MCP Server

A small, purpose-built MCP server exposing exactly four operations against the document graph (Neon Postgres: `documents` / `document_links` / `run_log`) — no arbitrary SQL, no schema access beyond these four tools. This is deliberately narrower than Neon's own official MCP server (`neondatabase/mcp-server-neon`), which is a general database-admin tool (arbitrary SQL, branch management, migrations) — too broad a capability to hand an autonomous agent. See [`docs/planning/notes/2026-08-06_document-graph-mcp-server_note.md`](../../planning/notes/2026-08-06_document-graph-mcp-server_note.md) for the full rationale.

## What it exposes

- `write_document(doc_type, title, content, created_by_agent, supersedes_id?)` — `doc_type` constrained to `recommendation | content | analysis | report`.
- `link_documents(from_doc_id, to_doc_id, relation)` — free-text `relation`; duplicate edges are silently ignored.
- `get_document(id)` — full content of one document.
- `list_documents(doc_type?, limit?)` — metadata only (no content), most recent first.
- `auto_link_similar_documents(document_id, threshold=0.85)` — embeds the document (if not already embedded) and auto-creates `related_to` links to any existing document above the cosine-similarity threshold. Called by every persona immediately after `write_document`. See [`docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md`](../../planning/notes/2026-08-06_auto-link-similar-documents_note.md).

Embeddings go through OpenRouter's `/v1/embeddings` (proxying `google/gemini-embedding-001`, requested at 768 dims via an undocumented-but-verified `dimensions` param) — reuses the same `OPENROUTER_API_KEY` as Hermes's chat models, kept as this container's own copy of the credential rather than mounting `hermes-data/.env`.

The Neon connection string (`DATABASE_URL_POOLED`) lives only in this container's own environment — never in Hermes's environment, never visible to whatever calls these tools.

## Running it

It's a service in `docker-compose.yml` (`document-graph-mcp`), built from `mcp-servers/document-graph/`. It runs `streamable-http` transport on port `8765`, **not published to the host** — reachable only from other containers on the same Docker Compose network, by service name (`http://document-graph-mcp:8765/mcp`).

```bash
# Build + start
docker compose up -d document-graph-mcp

# Rebuild after changing server.py or requirements.txt
docker compose build document-graph-mcp
docker compose up -d document-graph-mcp
```

### Why HTTP-on-internal-network instead of stdio-via-docker-exec

The original plan was stdio transport, with Hermes reaching it via `docker exec -i horology-document-graph-mcp python server.py` (matching how `hermes mcp serve` itself works). That requires mounting `/var/run/docker.sock` into Hermes's own container — which gives that container control over *every* container on the host, not just this one. Rejected as too broad a permission grant for an autonomous agent container. `streamable-http` with no host port published gives the same practical isolation (Hermes can reach only this one service, nothing else) without the Docker-socket escalation.

## Testing it directly (without a real MCP client)

```bash
# Confirm it's NOT reachable from the host (should fail to connect):
curl -sS http://localhost:8765/mcp

# Confirm it IS reachable from Hermes's container (400 is fine — that's the
# server correctly rejecting a bare GET without proper MCP session headers,
# not a networking failure):
docker exec horology-hermes curl -sS -o /dev/null -w "%{http_code}\n" http://document-graph-mcp:8765/mcp
```

## Connecting Hermes to it

```bash
printf "n\ny\n" | docker exec -i horology-hermes hermes mcp add document-graph --url http://document-graph-mcp:8765/mcp
```

The `printf "n\ny\n"` answers two interactive prompts non-interactively: "Does this server require authentication?" (no) and "Enable all N tools?" (yes). Verify with:

```bash
docker exec horology-hermes hermes mcp list
```

Verified end-to-end through Hermes itself (not just the raw protocol test above): asked Second-Soul directly whether the tool was available, and it correctly discovered and called `list_documents`.

## Dependency pinning

`requirements.txt` pins exact versions (`mcp==2.0.0`, not `>=`). The MCP Python SDK's API changed between versions during this project's own build — `FastMCP` (the class name assumed from prior knowledge) doesn't exist in `2.0.0`; the current class is `mcp.server.mcpserver.MCPServer`, same constructor/decorator/`run()` shape otherwise. Verify against the SDK's release notes before bumping the version.
