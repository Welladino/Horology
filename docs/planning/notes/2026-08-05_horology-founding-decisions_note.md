# Implementation Note

## Topic
- horology-founding-decisions

## Context

Solo founder building the Article Aggregator SaaS with no co-founder and no one interested in joining. Wanted a personal "AI co-founder" — a supervisor agent that dispatches to specialist subagents — to help with the non-engineering side of running the business, starting small and scaling the subagent roster over time.

Option-mapping and tradeoffs (orchestration framework, execution platform, document storage, commercialization) are in [`docs/planning/research/2026-08-05_horology-founding-options_research.md`](../research/2026-08-05_horology-founding-options_research.md). This note captures only the decisions actually made.

## Decision

**Scope and ownership**
- Build this as its own project (**Horology**), in its own repo, with its own database — not inside `Article_aggregator_agent`, and not sharing its DB or code.
- Keep the boundary clean: no importing this repo's code into Horology, even where reuse looks tempting, specifically so a future multi-tenant/microservice split doesn't require untangling shared dependencies later.
- Same harness can later be reused for full-time-job tasks, but only as a second, fully separate deployment (separate DB, separate keys, separate cron) — never sharing data with the business instance. Get explicit sign-off from the employer before wiring it to any real company data.

**Orchestration and execution platform**
- No third-party orchestration framework — use the platform-native mechanism (Hermes Agent's own).
- Execution platform: **Hermes Agent** (Nous Research), not Claude Code/Codex CLI, for automated runs — chosen specifically to keep scheduled automation cost/usage isolated from interactive coding capacity. Claude Code/Codex remain the tools for interactive coding work and for personally driving the system by hand.
- Embeddings/pgvector deferred; Temporal-style durable execution deferred; Obsidian ruled out (no logic value); OpenHands set aside for now, flagged as a fit for a future coding-focused subagent.

**Document graph: separate from Horology's own planning docs**
- `docs/planning/` (this repo) = how Horology itself gets built: research briefs, implementation notes, standing architecture reference, archived/superseded docs. Human-authored, git-versioned.
- A separate database (now built — see the document-graph MCP server note) = what Horology's agents produce while running: GTM docs, marketing reports, sourcing findings, etc. Schema: `documents` (content + `supersedes_id` self-FK for version chains), `document_links` (relation edges), `run_log` (audit trail).
- Reached via MCP from whichever orchestrator is running — the graph was never meant to live inside any one orchestrator's internals, so swapping orchestrators later doesn't require restructuring it.
- This also solves the multi-repo context problem: one shared, MCP-reachable store gives cross-repo recall without manual context-feeding.

**Commercialization: deferred, not designed for**
- If ever commercialized: keep Horology's boundary clean (own DB, own thin API/MCP surface) so a multi-tenant retrofit is additive, not a rewrite.

## Rationale

Every layer of this decision followed the same principle: use the platform-native orchestration mechanism rather than adding a third-party framework, and keep cost/vendor risk isolated from work that matters (coding capacity). The one genuine trade taken was accepting a newer, less-proven vendor (Hermes/Nous Research) in exchange for solving three real, stated problems at once: usage-bucket isolation, native fit for non-coding subagent roles, and a working GUI + messaging-based interaction loop without building either from scratch.

## Impact

- No code written at the time of this decision. Confirmed Horology's repo structure (`docs/planning/{research,notes,templates}`, `docs/architecture/`, `docs/archive/`) is orchestrator-agnostic — none of it assumed Claude Code, Hermes, or any other specific platform.
- Set up the next concrete steps that followed: hands-on trial of Hermes Agent, creating the document-graph database, defining the first subagent personas.

## Follow-Ups

- Revisit Temporal-style durable execution only if multi-day human-wait reliability becomes a real requirement.
- Revisit embeddings/pgvector once document volume makes structural filtering insufficient.
- Revisit OpenHands (+ optionally local Ollama models) specifically when/if a coding-focused subagent is added.
- Revisit commercialization/multi-tenancy only if real external demand appears — not a current design target.
