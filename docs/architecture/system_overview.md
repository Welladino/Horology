# System Overview

Standing reference for Horology's current architecture. Updated in place as the system evolves — for how a given piece of it came to be, see `docs/planning/notes/` and `docs/planning/research/`.

## What Horology is

A solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches work to named specialist subagents. The founder talks only to Second-Soul; subagents are never contacted directly. The goal is to offload recurring, judgment-lite business work (GTM strategy, marketing content, codebase/security monitoring, and more over time) so the founder's attention goes to decisions that actually need them.

This is a separate project from `Article_aggregator_agent` (the actual product/business) — no shared code, database, or credentials. See [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](../planning/notes/2026-08-05_horology-founding-decisions_note.md) for why.

## Runtime: three Docker containers

```
┌──────────────────────────┐
│   hermes                 │   Hermes Agent (Nous Research)
│   (horology-hermes)      │   - Second-Soul (default profile)
│                           │   - gtm-manager, marketing-executive,
│   127.0.0.1:8642 (API)   │     code-sentinel, ... (subagent profiles)
│   127.0.0.1:9119 (dash)  │
└─────────────┬─────────────┘
              │ internal Docker network only (no host port on either target)
    ┌─────────┴─────────┐
    ▼                   ▼
┌─────────────────┐  ┌──────────────────────┐
│ document-graph-  │  │ github-monitor-mcp    │
│ mcp              │  │                        │
│ :8765/mcp        │  │ :8766/mcp              │
│                   │  │                        │
│ -> Neon Postgres  │  │ -> GitHub API          │
│ (external)        │  │ (Article_aggregator_   │
│                   │  │  agent, read-only)      │
└─────────────────┘  └──────────────────────┘
```

- **`hermes`** — the agent runtime. Runs Second-Soul plus every subagent as its own Hermes **profile**: a fully separate identity with its own persona (`SOUL.md`), model config, memory, and tool/skill set — not an ephemeral one-shot delegation. Chosen over Claude Code/Codex CLI specifically to keep scheduled automation cost/usage isolated from interactive coding work (Claude Code's usage bucket is shared with interactive coding sessions). See the founding-decisions note above for the full platform comparison.
- **`document-graph-mcp`** — a purpose-built MCP server exposing 4 narrow tools (`write_document`, `link_documents`, `get_document`, `list_documents`) against a Neon Postgres database. Where agents write real, findable output. No arbitrary SQL is ever exposed.
- **`github-monitor-mcp`** — a purpose-built MCP server exposing 8 read-only tools against `Article_aggregator_agent` on GitHub (CI status, PRs, Dependabot alerts, code search, PR diffs, file content). No write capability anywhere, enforced at the credential level (a fine-grained PAT scoped to Read-only).

Neither MCP server publishes a host port — reachable only from `hermes`, over the internal Compose network, by service name. Each server holds its own credential in its own container's environment, never in Hermes's own environment — this is the standing security pattern for any future integration too. See [`docs/runbook/mcp/README.md`](../runbook/mcp/README.md) for the pattern to follow when adding a new one.

## Dispatch mechanism

Subagents are assigned work via **kanban tasks** (`hermes kanban create --assignee <profile>`), not Hermes's `delegate_task` primitive. `delegate_task` creates an anonymous, memory-less subagent per call and has a known output-truncation bug; kanban gives each subagent a persistent identity and a durable, queryable task/event history. See [`docs/planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md`](../planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md).

Every subagent must call `kanban_complete` (or `kanban_block` with a reason) to close out a task — a task that just stops is flagged as a `protocol_violation` and silently retried. Each subagent profile has a turn budget (`agent.max_turns`, currently 50) with a structured `timed_out` event if it runs out before finishing.

## Document graph

Business documents (recommendations, content, analysis, reports) produced by any subagent live in a Postgres database (Neon), reached only through `document-graph-mcp`'s tools — not Hermes's own session/kanban state, which is local-machine-only and gitignored. The graph is deliberately orchestrator-agnostic: it was designed to be reachable via MCP from any future orchestrator, not tied to Hermes specifically.

Schema: `documents` (content + `supersedes_id` self-FK for version chains), `document_links` (`from_doc_id`/`to_doc_id`/`relation` edges), `document_embeddings` (768-dim vector per document, HNSW index, via OpenRouter's `/v1/embeddings` proxying `google/gemini-embedding-001` — same OpenRouter key as chat, not a separate Gemini/GCP key), `run_log` (reserved for Second-Soul's own top-level activity audit trail — not yet used; kanban's own task history currently covers subagent-level audit). See [`docs/runbook/db/alembic_workflow.md`](../runbook/db/alembic_workflow.md) for the migration workflow.

**Auto-linking:** every persona calls `auto_link_similar_documents(document_id)` immediately after `write_document` — this embeds the new document and auto-creates `related_to` edges to any existing document above a cosine-similarity threshold (default 0.85), so semantically related documents get connected even when they share almost no vocabulary. See [`docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md`](../planning/notes/2026-08-06_auto-link-similar-documents_note.md).

For the rules on *when* and *how* a subagent should write a document, see [`CLAUDE.md`](../../CLAUDE.md).

## Personas

`personas/supervisor/SOUL.md` and `personas/subagents/*.md` in this repo are the git-tracked source of truth. `hermes-data/` (gitignored) holds the actual runtime copies Hermes reads from — always edit the repo copy and sync, never edit `hermes-data/` directly. `personas/subagents/INDEX.md` is a lightweight lookup (name, one-line scope, path) Second-Soul reads first, so its own system prompt doesn't grow unboundedly as the subagent roster expands — full persona text is only loaded once a specific subagent is actually needed.

## Current subagent roster

| Profile | Role | External access |
|---|---|---|
| `gtm-manager` | GTM strategy, positioning, channel/sequencing recommendations | document-graph only |
| `marketing-executive` | Copy, content drafts, campaign execution | document-graph only |
| `code-sentinel` | CI/PR/security monitoring for `Article_aggregator_agent` | document-graph + github-monitor |

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
| `document-graph` MCP (4 tools) | ✓ | ✓ | ✗ none |
| `github-monitor` MCP (8 tools) | ✓ | `code-sentinel` only | ✗ none |
| **`agent.max_turns`** (overall ceiling, all tools combined) | 150 | 50 | ✓ per turn |

**No general per-tool call-count mechanism exists in Hermes** — `tool_loop_guardrails.loop_caps` is hardcoded to exactly two names, `max_web_searches` and `max_subagents`; nothing else (including custom MCP tools) can get a native hard cap. `agent.max_turns` is the only backstop against any other single tool being called repeatedly — it bounds the total budget, not any one tool's share of it. Deliberately not using soft (persona-instructed, unenforced) caps to approximate this gap — see [`docs/planning/notes/2026-08-06_tool-surface-cleanup_note.md`](../planning/notes/2026-08-06_tool-surface-cleanup_note.md).
