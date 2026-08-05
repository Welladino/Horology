# Implementation Note

## Topic
- document-graph-mcp-server

## Context

While solving the delegate_task output-truncation bug and the "write structured documents" requirement, the first attempt built a Hermes *skill* (`write-document`) whose scripts (`write_document.mjs`, `link_documents.mjs`) held the raw Neon connection string and were invoked by the agent via its generic `terminal`/`code_execution` tools.

This was stopped and reverted (deleted, never committed) after the founder raised two objections: (1) agents should not execute arbitrary code unless truly necessary, and (2) if they do, credentials must not be directly reachable from that execution context — the model cited is a sandboxed/scoped-secrets pattern ("the Vercel method") rather than a raw shell with env vars in scope.

Separately, looked at whether Neon's own official MCP server (`neondatabase/mcp-server-neon`) could be used instead of building anything. It's a general database-admin tool — arbitrary SQL execution, branch/project management — aimed at a developer managing infrastructure conversationally. Connecting Hermes to it would hand an autonomous agent the same "arbitrary code + real credentials" problem just repackaged as an MCP server, not resolve it.

## Decision

Built a small, purpose-specific MCP server instead of either option:

- **Location:** `mcp-servers/document-graph/` (Python, using the official `mcp` SDK).
- **Surface:** exactly four tools — `write_document`, `link_documents`, `get_document`, `list_documents` — each running one fixed, parameterized query. No arbitrary SQL is ever exposed to a caller.
- **Credential isolation:** `DATABASE_URL_POOLED` lives only in this server's own container environment (`document-graph-mcp` service in `docker-compose.yml`), never in Hermes's environment (`hermes-data/.env`) and never visible to whatever calls the tools. This directly satisfies the "credentials must not be reachable from execution context" requirement — the agent gets a named, typed tool call, not a shell with the DB password in scope.
- **Transport:** stdio, matching how `hermes mcp serve` itself works — no exposed network port. The container idles (`sleep infinity`); the actual server process is invoked per-connection via `docker exec -i horology-document-graph-mcp python server.py`.
- **Removed:** the discarded skill (`skills/document-graph/write-document/`) was deleted entirely — it was never committed to git, so no history to clean up, but the stale copy inside `hermes-data/skills/` and the stray `DATABASE_URL_POOLED` line it had added to `hermes-data/.env` (Hermes's own env file) were also removed, since Hermes itself should never hold this credential.

**Verified working, over the real protocol, not just unit-tested in isolation:** MCP `initialize` handshake, `tools/list` (all four tools present with correct input schemas), and a live `write_document` call that produced a real row in Neon — confirmed by querying the DB directly afterward.

**Bug found during verification, not in our code:** the installed `mcp` SDK version (2.0.0) doesn't have the `mcp.server.fastmcp.FastMCP` class assumed from prior knowledge — it's `mcp.server.mcpserver.MCPServer` at a different import path, though the constructor/`@tool()`/`.run()` interface is otherwise the same. `requirements.txt` now pins `mcp==2.0.0` exactly (not `>=`) with a comment flagging this, rather than floating and risking the same surprise again on a future rebuild.

## Rationale

The founder's objection wasn't about code execution being unsafe in the abstract — it was specifically that an autonomous, scheduled agent holding a real database credential and running self-directed scripts is a different risk class than a human developer doing the same thing interactively. An MCP server with a fixed tool surface is the correct mechanism for "the agent needs a narrow, specific capability" without that capability becoming "the agent has a shell." Neon's own MCP server was rejected for the same underlying reason as the original skill — breadth of access, not authorship — even though it would have been faster to adopt.

## Impact

- Establishes the pattern for any future capability an agent needs against a real system with credentials: build a small, single-purpose MCP server exposing named operations, not a skill that shells out with a raw credential in scope.
- `hermes-data/.env` now correctly holds only Hermes's own provider key (OpenRouter) — the Neon credential lives exclusively in the new `document-graph-mcp` service's environment.
- Hermes is not yet connected to this server (see Follow-Ups) — the server is verified standalone, but the `delegate_task` truncation-bug workaround (subagent writes its full answer via this MCP tool instead of returning it inline) is still untested end-to-end through Hermes itself.

## Follow-Ups

- Register this server with Hermes via `hermes mcp add` (or equivalent), using the `docker exec -i horology-document-graph-mcp python server.py` command as the stdio transport.
- Once connected, retest the GTM Manager delegation from the truncation-bug note, this time having the subagent call `write_document` directly instead of relying on `delegate_task`'s return value.
- Update the `write-document`-skill references in earlier notes (subagent-index-lazy-loading note, delegation-output-truncation-bug note) to point at this MCP server instead, once subagent personas are updated to reference it.
