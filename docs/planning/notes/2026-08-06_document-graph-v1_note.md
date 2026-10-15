# Document graph, first version: server, embeddings, linking and upkeep

## Topic
- document-graph-v1

## Context

Agents needed somewhere durable to write structured business documents, and a way around the `delegate_task` truncation bug. The first attempt (2026-08-06) was a Hermes skill whose scripts held the raw Neon connection string and ran through `terminal`/`code_execution`. It was deleted before being committed: the founder objected that an autonomous, scheduled agent should not execute arbitrary code, and that a credential must never be reachable from that context. Neon's official MCP server was also rejected: it offers arbitrary SQL and project management, the same problem in different packaging.

## Decisions

**A purpose-built MCP server (2026-08-06).** `mcp-servers/document-graph/` exposed four tools (`write_document`, `link_documents`, `get_document`, `list_documents`), each one fixed, parameterised query. The Neon credential lives only in that container, never in Hermes' environment. It started on stdio and moved to HTTP on the internal Docker network with no host port. Verified over the real protocol: handshake, `tools/list` and a live write confirmed in the database. The installed `mcp` 2.0.0 SDK has `mcp.server.mcpserver.MCPServer`, not the `FastMCP` class assumed from memory, so the version is pinned exactly.

**Embeddings and automatic linking (2026-08-06).** Approach: [document-linking research](../research/2026-08-06_document-linking-approach_research.md). Migration `20260806_001` added `document_embeddings` (`vector(768)`, HNSW cosine index), and `auto_link_similar_documents(document_id, threshold=0.85)` embeds a document and adds `related_to` links above the threshold. Embeddings use OpenRouter's `/v1/embeddings` proxying `google/gemini-embedding-001`, reusing the existing OpenRouter key, so no new GCP key was needed. Two wrong assumptions were caught by live calls: the model returns 3,072 dimensions by default, which also exceeds pgvector's 2,000-dimension HNSW limit; and OpenRouter, despite not documenting it, passes `"dimensions": 768` through to Gemini. Every embed call now requests 768 explicitly. In a live run, document 5 linked to document 6 at 0.857, and the unrelated document 7 linked to nothing, confirmed in `document_links` directly. Every persona calls `auto_link_similar_documents` straight after `write_document`.

**Reading the graph back and catching gaps (2026-08-07).** `get_related_documents` returns a document's incoming and outgoing links; `list_unembedded_documents` finds documents left without an embedding, because writing and linking are separate calls. Decided against a new "linker" profile (the clean-up needs no judgment), topic tagging (embeddings already find related content across wording), a retroactive re-comparison sweep (each new document is compared with every existing one at write time, so the graph self-heals), and giving any profile code execution for the clean-up.

**Daily embedding sweep (2026-08-07).** Design: [cron script research](../research/2026-08-07_cron-script-security-pattern_research.md). Migration `20260807_001` created the read-only login `horology_cron_sweep_ro` (SELECT on `documents` and `document_embeddings` only; INSERT and other tables were checked to fail). `scripts/check_unembedded_documents.py` runs under Hermes' bundled Python, which has `asyncpg` but not `psycopg2`. The planned two-job `context_from` chain isn't exposed by `hermes cron create`; one job uses the `wakeAgent` gate instead: a final stdout line `{"wakeAgent": false}` skips the agent at no model cost, and anything else wakes it with the script output in its prompt. A probe job verified both paths before the real job `document-graph-embedding-sweep` (daily 09:00 UTC) was created and returned `wakeAgent: false` on the fully embedded graph.

**Near-duplicate signal (2026-08-07).** When `auto_link_similar_documents` reports a score at or above a higher bar, the agent says "near-duplicate of doc #N" in its `kanban_complete` summary rather than letting it look like an ordinary link; it still writes the document. The bar started at 0.95. The first real recurring case, two `code-sentinel` reports a day apart on a dormant repository (same 30 Dependabot alerts, same missing CI), scored 0.9343, independently recomputed in SQL. The agent called it a near-duplicate anyway, the right judgment, so the threshold was lowered to 0.90 in `CLAUDE.md` and the `code-sentinel` persona.

## Rationale

Narrow named tools instead of a shell holding a credential, and every claim that would become load-bearing (vector width, index limits, an undocumented parameter, a CLI flag, which driver is importable) checked with a real call first, because those mistakes fail silently or much later.

## Impact

- The pattern for any agent capability against a real system: a small MCP server with named operations and its own credential.
- The graph has since grown into passage search, topics, entities, workspaces and a sheet sync ([architecture](../../architecture/mcp/document-graph.md)).

## Follow-Ups

- 0.85 and 0.90 rest on one real recurring pair; revisit once there is a distribution of day-over-day scores, including whether real news on a repository scores clearly below 0.90.
- The sweep's "found something" path has been verified only with the probe, not with real non-empty output.
- The 768-dimension request relies on undocumented OpenRouter behaviour; re-check if the provider or model changes.
