# CLAUDE.md

This file provides guidance to Claude Code (or any agent) working in this repository.

## Project Overview

Horology is a solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches work to named specialist subagents. The founder talks only to Second-Soul; subagents are never contacted directly. The goal is to offload recurring, judgment-lite business work (GTM strategy, marketing content, codebase/security monitoring, and more over time) so the founder's attention goes to decisions that actually need them.

This is a **separate project from `Article_aggregator_agent`** (the actual product/business) — deliberately: no shared code, no shared database, no shared credentials. See [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](docs/planning/notes/2026-08-05_horology-founding-decisions_note.md) for why.

## Architecture

Three Docker containers (`docker-compose.yml`), on an isolated Compose network:

- **`hermes`** — [Hermes Agent](https://hermes-agent.nousresearch.com/) (Nous Research), the agent runtime. Runs Second-Soul (the default profile) plus every subagent as its own Hermes **profile** — a fully separate identity (own persona, model config, memory, tool/skill set), not an ephemeral one-shot delegation. Chosen over Claude Code/Codex CLI specifically to keep scheduled automation cost/usage isolated from interactive coding work.
- **`document-graph-mcp`** — a purpose-built MCP server exposing 4 narrow tools (`write_document`, `link_documents`, `get_document`, `list_documents`) against a Neon Postgres database. This is where agents write real, findable output.
- **`github-monitor-mcp`** — a purpose-built MCP server exposing 8 read-only tools against `Article_aggregator_agent` on GitHub (CI status, PRs, Dependabot alerts, code search, etc.).

Neither MCP server publishes a host port — reachable only from `hermes`, over the internal Docker network, by service name. Each server holds its own credential, in its own container's environment, never in Hermes's own environment. See [`docs/runbook/mcp/README.md`](docs/runbook/mcp/README.md) for the full pattern and how to add a new one.

**Dispatch mechanism:** subagents are assigned work via **kanban tasks** (`hermes kanban create --assignee <profile>`), not Hermes's `delegate_task` primitive — `delegate_task` has a known output-truncation bug and no persistent identity for the subagent. See [`docs/planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md`](docs/planning/notes/2026-08-06_migrate-to-kanban-profiles_note.md).

## Repo Layout

- `personas/supervisor/SOUL.md` — Second-Soul's persona, git-tracked source of truth.
- `personas/subagents/*.md` — each subagent's persona, git-tracked source of truth. `INDEX.md` is the lightweight lookup Second-Soul reads first (name, one-line scope, path) — full persona text is never loaded until a specific subagent is actually needed, to keep Second-Soul's own system prompt from growing unboundedly with the roster.
- `mcp-servers/<name>/` — one purpose-built MCP server per external system (`server.py`, `requirements.txt`, `Dockerfile`).
- `alembic/` — migrations for the document-graph schema on Neon. See [`docs/runbook/db/alembic_workflow.md`](docs/runbook/db/alembic_workflow.md).
- `hermes-data/` — **gitignored.** All of Hermes's actual runtime state (config, sessions, every profile's own subfolder, kanban tasks). Persona files here are *copies*, synced from `personas/` — always edit the repo copy and re-sync, never edit `hermes-data/` directly as the source of truth.
- `docs/planning/{research,notes}/` — see below.
- `docs/architecture/`, `docs/archive/`, `docs/runbook/` — standing reference, superseded docs, and practical how-to, respectively (same convention as `Article_aggregator_agent`).

## How Subagents Should Create Documents

Any subagent (or Second-Soul itself) that produces a **finished, substantive output** — not ordinary conversation or intermediate reasoning — should write it to the document graph via the `write_document` MCP tool, not return it inline or leave it only in a kanban task summary.

**The rule for what counts:** a document is something a founder or another agent might want to find, reference, or build on months later. A GTM recommendation, a piece of marketing copy, a security findings report — yes. "Let me check the index" or routine back-and-forth — no.

**`doc_type` must be one of:**
- `recommendation` — "here's what I think we should do and why" (e.g. GTM Manager's channel/strategy calls).
- `content` — usable output artifacts: copy, campaign drafts, written material (e.g. Marketing Executive's drafts).
- `analysis` — findings/observations without an explicit recommendation attached (e.g. Code Sentinel's repo health reports).
- `report` — a status/summary rollup, typically time-boxed (e.g. Second-Soul's own periodic status reports).

**Practical conventions, already enforced in every subagent persona:**
- Write the **full** answer as `content` — assume the founder reads the document standalone, without also re-reading the persona or the original task.
- Set `created_by_agent` to the profile name (e.g. `"gtm-manager"`), for traceability.
- Use `supersedes_id` when a new document replaces an earlier one's conclusion (creates a version chain, not an orphaned duplicate) — use `link_documents` with a `relation` like `related_to`/`informed_by`/`contradicts` when two documents are connected but neither replaces the other.
- **Kanban tasks must still call `kanban_complete`/`kanban_block`** after writing — the document graph and the kanban protocol are separate systems; writing a document doesn't close out a task on its own.
- Keep the kanban completion summary brief (a one-line pointer to the document id/title) — the full content lives in the document, not duplicated into the kanban summary or the subagent's own memory.

This keeps documents durable and queryable independent of Hermes's own session/kanban state (which is gitignored, local-machine-only), and independent of which orchestrator is running the subagent — the document graph was designed to be reachable by any future orchestrator via MCP, not tied to Hermes specifically.

## Working in This Repo

- **Personas are edited in `personas/`, then synced into the running container** — editing `hermes-data/` directly is invisible to git and will be lost on rebuild. See [`docs/runbook/docker/hermes_setup.md`](docs/runbook/docker/hermes_setup.md) for the sync commands.
- **New subagent checklist:** persona file in `personas/subagents/`, real Hermes profile (`hermes profile create`), explicit model config in the profile's `config.yaml` (not `profile.yaml`, which is metadata-only), skills trimmed to a justified minimum (`skills opt-out --remove`, then add back only what's needed), unnecessary toolsets disabled (`computer_use`, `code_execution`, `terminal`, `delegation`, `cronjob` unless the role genuinely needs them), MCP servers connected per-profile (connections are not shared across profiles), a row added to `personas/subagents/INDEX.md`. Full command sequence in `docs/runbook/docker/hermes_setup.md`.
- **Before editing `config.yaml` on disk:** don't, while Hermes is running — the live gateway process holds its own in-memory config and silently reverts direct file edits. Use `hermes config set` / equivalent CLI commands instead.
- **When adding a new external integration** (a new MCP server): match the existing pattern — narrowest justified tool surface, own container, own credential never shared with Hermes's environment, no published host port, verify isolation directly (unreachable from host, reachable from Hermes) before connecting anything. See [`docs/runbook/mcp/README.md`](docs/runbook/mcp/README.md).
- **Verify claims hands-on before designing around them.** This project has hit multiple cases where documentation (or a first-pass research pass) gave a wrong or stale answer that a cheap, direct test corrected — e.g. a claimed-nonexistent kanban timeout signal that turned out to exist and be queryable. Prefer a real test over trusting docs when the design will depend on the answer.
- **Planning docs:** `docs/planning/research/` for open questions/investigation, `docs/planning/notes/` for decisions actually made and implemented — don't merge both into one file if there's a genuine investigation phase worth preserving separately. See `docs/planning/README.md` for the full workflow and templates.
