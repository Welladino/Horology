# System Overview

Standing reference for Horology's current architecture. Updated in place as the system evolves — for how a given piece of it came to be, see `docs/planning/notes/` and `docs/planning/research/`.

## What Horology is

A solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches work to named specialist subagents. The founder talks only to Second-Soul; subagents are never contacted directly. The goal is to offload recurring, judgment-lite business work (GTM strategy, marketing content, codebase/security monitoring, and more over time) so the founder's attention goes to decisions that actually need them.

This is a separate project from `Article_aggregator_agent` (the actual product/business) — no shared code, database, or credentials. See [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](../planning/notes/2026-08-05_horology-founding-decisions_note.md) for why.

## Runtime: main stack and restricted gateway

The main Compose stack runs Hermes and document-graph-mcp. Document graph listens on port 8765 only inside the Docker network, persists business outputs to Neon, and uses OpenRouter embeddings. Its seven narrow document tools expose no arbitrary SQL.

The restricted mcp-gateway runs in its own Compose project on localhost port 8767. The optional compose.hermes-network.yaml joins the existing horology_default network under alias horology-mcp-gateway. Both Second-Soul and Code Sentinel connect to it with separate authenticated GitHub-only assignments. Repository access comes from policy and assignment intersection; both assignments currently cover Welladino/Horology and Welladino/Article_aggregator_agent. Provider credentials remain in gateway .env.local, never in Hermes; Hermes holds only its gateway bearer credentials. The old github-monitor server and Compose service are retired.

The gateway exposes seventeen tools; Hermes monitoring profiles select only gateway_status plus nine GitHub tools. Local assignments expire after 24 hours, and per-tool usage persists across restarts. Scheduling still requires fresh assignment provisioning per run. The standalone gateway's localhost port requires authentication. Document graph publishes no host port and currently relies on internal network isolation; public cloud authentication remains future work.

## Dispatch mechanism

Subagents are assigned work via **kanban tasks** (`hermes kanban create --assignee <profile>`), not Hermes's `delegate_task` primitive. `delegate_task` creates an anonymous, memory-less subagent per call and has a known output-truncation bug; kanban gives each subagent a persistent identity and a durable, queryable task/event history. See [`docs/planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md`](../planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md).

Every subagent must call `kanban_complete` (or `kanban_block` with a reason) to close out a task — a task that just stops is flagged as a `protocol_violation` and silently retried. Each subagent profile has a turn budget (`agent.max_turns`, currently 50) with a structured `timed_out` event if it runs out before finishing.

## Document graph

Business documents (recommendations, content, analysis, reports) produced by any subagent live in a Postgres database (Neon), reached only through `document-graph-mcp`'s tools — not Hermes's own session/kanban state, which is local-machine-only and gitignored. The graph is deliberately orchestrator-agnostic: it was designed to be reachable via MCP from any future orchestrator, not tied to Hermes specifically.

Schema: `documents` (content + `supersedes_id` self-FK for version chains), `document_links` (`from_doc_id`/`to_doc_id`/`relation` edges), `document_embeddings` (768-dim vector per document, HNSW index, via OpenRouter's `/v1/embeddings` proxying `google/gemini-embedding-001` — same OpenRouter key as chat, not a separate Gemini/GCP key), `run_log` (reserved for Second-Soul's own top-level activity audit trail — not yet used; kanban's own task history currently covers subagent-level audit). See [`docs/runbook/db/alembic_workflow.md`](../runbook/db/alembic_workflow.md) for the migration workflow.

**Auto-linking:** every persona calls `auto_link_similar_documents(document_id)` immediately after `write_document` — this embeds the new document and auto-creates `related_to` edges to any existing document above a cosine-similarity threshold (default 0.85), so semantically related documents get connected even when they share almost no vocabulary. See [`docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md`](../planning/notes/2026-08-06_auto-link-similar-documents_note.md).

**Reading the graph back:** `get_related_documents(document_id)` returns a document's outgoing/incoming `document_links` edges (title, doc_type, relation, direction) — the read side of the graph auto-linking builds. `list_unembedded_documents()` returns any document with no stored embedding yet (written before auto-linking existed, or where a prior `auto_link_similar_documents` call was skipped or failed) — the detection mechanism for the gap that `write_document` and `auto_link_similar_documents` being separate, non-atomic calls leaves open. See [`docs/planning/notes/2026-08-07_document-graph-completeness-punch-list_note.md`](../planning/notes/2026-08-07_document-graph-completeness-punch-list_note.md).

For the rules on *when* and *how* a subagent should write a document, see [`CLAUDE.md`](../../CLAUDE.md).

## Personas

`personas/supervisor/SOUL.md` and `personas/subagents/*.md` in this repo are the git-tracked source of truth. `hermes-data/` (gitignored) holds the actual runtime copies Hermes reads from — always edit the repo copy and sync, never edit `hermes-data/` directly. `personas/subagents/INDEX.md` is a lightweight lookup (name, one-line scope, path) Second-Soul reads first, so its own system prompt doesn't grow unboundedly as the subagent roster expands — full persona text is only loaded once a specific subagent is actually needed.

## Current subagent roster

| Profile | Role | External access |
|---|---|---|
| `gtm-manager` | GTM strategy, positioning, channel/sequencing recommendations | document-graph only |
| `marketing-executive` | Copy, content drafts, campaign execution | document-graph only |
| `code-sentinel` | CI/PR/security monitoring for policy-approved repos | document-graph + mcp-gateway |

Planned, not yet built: a combined DevOps/Infra subagent covering GCP and Supabase monitoring.

## Toolset and caps

Second-Soul has the broadest toolset; the three subagents share an identical, further-trimmed set (no `terminal`, `code_execution`, `browser`, `delegation`, `cronjob` — none of their actual work needs shell/code execution or browser automation, and `delegation`/`cronjob` don't fit their "only act when assigned a kanban task" role).

| Tool | Second-Soul | Subagents | Native cap? |
|---|---|---|---|
| `web_search` | ✓ | ✓ | ✓ 10 calls/turn (`tool_loop_guardrails.loop_caps.max_web_searches`) |
| `web_extract` | ✓ | ✓ | ✗ none — Hermes has no equivalent key for extract, confirmed by testing (`config set` flags it unrecognized) |
| `browser` | ✗ disabled | ✗ disabled | — |
| `terminal` | ✗ disabled | ✗ disabled | — |
| `code_execution` | ✗ disabled | ✗ disabled | — |
| `file` | ✓ | ✓ | ✗ none (but single-read size is bounded by `file_read_max_chars`, default 100k) |
| `skills`, `todo`, `memory`, `session_search`, `clarify` | ✓ | ✓ | ✗ none |
| `delegation` | ✓ (unused — kanban replaced `delegate_task`) | ✗ disabled | ✓ `delegation.max_iterations` (50), effectively moot now |
| `cronjob` | ✓ | ✗ disabled | — |
| `document-graph` MCP (7 tools) | ✓ | ✓ | ✗ none |
| `mcp-gateway` GitHub tools | ✓ | `code-sentinel` only | ✗ none |
| **`agent.max_turns`** (overall ceiling, all tools combined) | 150 | 50 | ✓ per turn |

**No general per-tool call-count mechanism exists in Hermes** — `tool_loop_guardrails.loop_caps` is hardcoded to exactly two names, `max_web_searches` and `max_subagents`; nothing else (including custom MCP tools) can get a native hard cap. `agent.max_turns` is the only backstop against any other single tool being called repeatedly — it bounds the total budget, not any one tool's share of it. Deliberately not using soft (persona-instructed, unenforced) caps to approximate this gap — see [`docs/planning/notes/2026-08-06_tool-surface-cleanup_note.md`](../planning/notes/2026-08-06_tool-surface-cleanup_note.md).

## Restricted gateway migration

Second-Soul and Code Sentinel use the authenticated mcp-gateway for policy-approved GitHub reads. Provider implementations and MCP tools are separate modules. Gateway local Code Sentinel assignment expires after 24 hours, with two invocations per tool. Recurring assignment provisioning remains pending. The optional gateway Compose override joins the Hermes network; client-side tool filtering and server-side assignment policy both restrict Code Sentinel to GitHub.

Document graph stays separate. Its entrypoint registers seven operations from document_graph/tools.py backed by document_graph/client.py. It has its own pinned requirements and private mcp-servers/document-graph/.env loaded by root Compose; DATABASE_URL_POOLED and OPENROUTER_API_KEY are required, EMBED_MODEL is optional. Public cloud authentication and embedding budgets remain pending.

## MCP logging and failure handling

Both MCP services emit argument-free JSON operation events to stdout with correlation IDs, duration and outcome. Gateway events include the authenticated assignment. Clients receive sanitized error categories with a request ID, rather than raw provider/database exceptions. Automatic retries are disabled. Neon has five-second connection, ten-second statement and three-second lock timeouts; existing HTTP/Supabase timeouts remain. Standard transport/access logs remain separate from the application JSON events.

MCP timeouts and error/logging policy have a single source under `shared-runtime/horology_runtime/`: settings.py holds immutable timeout values and operations.py implements safe error categories and structured operation logging. Both images install this package, and the common root .dockerignore excludes private configuration from the larger build context.
