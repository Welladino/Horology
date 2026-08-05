# Implementation Note

## Topic
- horology-founding-decisions

## Context

Solo founder building the Article Aggregator SaaS with no co-founder and no one interested in joining. Explored building a personal "AI co-founder" — a supervisor agent that dispatches to specialist subagents (GTM manager, marketing executive, DB engineer, DevOps, sourcing, strategy, etc.) — to help with the non-engineering side of running the business (selling, GTM, ops monitoring), starting small and scaling the subagent roster over time.

This note captures the option-mapping and decisions made before any code was written, so the reasoning isn't lost.

## Decision

**Scope and ownership**
- Build this as its own project (**Horology**), in its own repo, with its own Supabase project — not inside `Article_aggregator_agent`, and not sharing its DB or code.
- Keep the boundary clean: no importing this repo's code (e.g. embedding logic) into Horology, even where reuse looks tempting, specifically so a future multi-tenant/microservice split doesn't require untangling shared dependencies later.
- Same harness can later be reused for full-time-job tasks, but only as a second, fully separate deployment (separate DB, separate keys, separate cron) — never sharing data with the business instance. Get explicit sign-off from the employer before wiring it to any real company data.

**Orchestration layer: no framework needed**
- Ruled out building a harness from scratch and ruled out LangChain/LangGraph/CrewAI/AutoGen/Google ADK's competitors as unnecessary. Claude Code, Codex, Google ADK, and Hermes Agent all already ship native supervisor-dispatches-to-subagents orchestration. A third-party framework only earns its place for a hand-authored deterministic control-flow graph or genuinely mixing multiple vendors' agents in one orchestration — neither applies here.
- Ruled out Temporal for now: it's a general durable-execution engine (survives crashes/long waits for arbitrary code), a different and heavier layer than what's needed at this scale. Worth revisiting only if "must survive crashes across multi-day human-wait periods" becomes a real reliability requirement.
- Ruled out Obsidian: no logic value (not agent-queryable, not structurally relational) — pure human-readable sugar not needed yet.
- Ruled out embeddings/pgvector for now: Claude does not do vector math itself (that requires a separate embedding model + vector store + retrieval glue, built outside the model). At Horology's expected document volume, structural filtering (list/filter by type, date, tag) is sufficient; add semantic search later only once manual filtering actually becomes painful. If/when needed, write a small standalone wrapper against an embeddings API directly rather than importing `Article_aggregator_agent`'s `similarity.py` / `gemini_embed.py` (small enough — under 100 lines combined — that duplicating is cheaper than coupling two services that may end up in different GCP projects).

**Execution platform: Hermes Agent (Nous Research), not Claude Code/Codex CLI, for the automated runs**
- Claude Code and Codex CLI were the original default (ride existing subscriptions, zero marginal cost, native subagent mechanism via `.claude/agents/*.md`).
- Reversed this after confirming Claude Code's usage bucket is shared across Claude Code, Claude.ai chat, and Cowork. Scheduled automation competing with live coding sessions risked starving actual coding capacity mid-workday — a worse failure mode than a small API bill.
- Hermes Agent fits the actual requirements well: general-purpose (not coding-specific, unlike OpenHands), model-agnostic (200+ backends via OpenRouter or direct provider keys), native multi-agent orchestrator+subagent pattern, native cron/scheduling with a `no_agent=True` script-only mode for pure watchdogs (DB/DevOps monitoring) that don't need to burn an LLM call, MCP support (for the Supabase doc-graph and other tools), multi-platform message delivery (Telegram/Slack/etc. — usable for the report-and-wait-for-reply loop), and a native desktop GUI (Hermes Desktop, public preview June 2026) plus Open WebUI as a web frontend option.
- Estimated cost via OpenRouter with a cheap model (e.g. DeepSeek V4 Flash): roughly $1-15/month for a twice-daily supervisor + a few subagent dispatches — small and on a budget fully separate from the Claude Code coding-limit bucket.
- Deployment: Modal is a natively supported Hermes execution backend, scales to zero, bills per second of actual use; free Starter tier includes $30/month compute credits, very likely sufficient for a twice-daily, non-GPU workload.
- Caveat accepted: Hermes (and Hermes Desktop specifically) is new/fast-moving (~221k GitHub stars as of July 2026, June 2026 GUI preview) — worth a hands-on trial before committing real business workflows to it.
- Claude Code/Codex remain the tool of choice for interactive coding work and for personally "poking" the system by hand — not removed from the toolkot, just not the automation backbone.
- OpenHands (also model-agnostic, MIT-licensed) was evaluated and set aside as the wrong fit for this project's roster (it's coding-agent-first; Horology's subagents are mostly non-coding roles). Flagged as a good fit specifically for future subagents that need to write/run code, especially paired with a local model via Ollama for high-frequency mechanical tasks at near-zero marginal cost.

**Document graph: separate from Horology's own planning docs**
- `docs/planning/` (this repo) = how Horology itself gets built: research briefs, implementation notes, standing architecture reference, archived/superseded docs. Human-authored, git-versioned.
- A separate Supabase project (not yet created) = what Horology's agents produce while running: GTM docs, marketing reports, sourcing findings, etc. Schema sketched as four tables:
  - `documents` — content + `supersedes_id` self-FK for versioning/history as a traceable chain, not just timestamps.
  - `document_links` — `from_doc_id` / `to_doc_id` / `relation` (informed_by, supersedes, contradicts, references) — the actual graph structure, traversable by SQL.
  - `document_embeddings` — deferred (see embeddings decision above).
  - `run_log` — every supervisor/subagent run: what was asked, decided, produced, linked to the documents it touched — the human-readable audit trail, distinct from the raw doc graph.
- Reached via MCP from whichever orchestrator is running (Hermes now, potentially Claude Code/Codex/ADK later) — the graph was never meant to live inside any one orchestrator's internals, so swapping orchestrators later doesn't require restructuring it.
- This also solves the multi-repo context problem: plain per-repo local files can't be queried across repos/projects; one shared Supabase project reachable via MCP from any repo gives cross-repo recall (e.g. a decision made in Horology's own build 6 months ago, or eventually across other unrelated repos) without manual context-feeding.

**Commercialization: deferred, not designed for**
- "AI co-founder" is already a funded, marketed commercial category (e.g. Tanka, ai.com) — productizing this would mean competing with well-resourced players on a thin moat (prompts + orchestration alone), unlike the actual product (sourced/curated content + delivery pipeline) which has real differentiation.
- If ever commercialized: keep Horology's boundary clean (own DB, own thin API/MCP surface) so a multi-tenant retrofit (tenant_id scoping, same pattern as `api/middleware/tenant_policy.py` in `Article_aggregator_agent`) is additive, not a rewrite. Cross-service/cross-GCP-project auth becomes a normal service-to-service integration problem only if the boundary was kept clean from the start.

## Rationale

Every layer of this decision followed the same principle: use the platform-native orchestration mechanism at whichever layer you're operating (CLI, SDK, or hosted agent framework) rather than adding a third-party framework on top, and keep cost/vendor risk isolated from work that matters (coding capacity). The one genuine trade taken was accepting a newer, less-proven vendor (Hermes/Nous Research, and MiniMax if MaxHermes is used) in exchange for solving three real, stated problems at once: usage-bucket isolation from coding work, native fit for non-coding subagent roles (monitoring, GTM, marketing), and a working GUI + messaging-based interaction loop without building either from scratch.

## Impact

- No code written yet. This note documents the pre-build decision-making only.
- Confirms Horology's repo structure (already scaffolded: `docs/planning/{research,notes,templates}`, `docs/architecture/`, `docs/archive/`) is orchestrator-agnostic — none of it assumes Claude Code, Hermes, or any other specific platform, so the Hermes decision doesn't require restructuring anything already committed.
- Sets up the next concrete steps: (1) hands-on trial of Hermes Agent + Hermes Desktop, (2) create the second Supabase project and apply the four-table doc-graph schema, (3) define the first 2-3 subagent persona files (recommended starting roster: GTM manager + marketing executive, per earlier scoping).

## Follow-Ups

- Revisit Temporal-style durable execution only if multi-day human-wait reliability becomes a real requirement.
- Revisit embeddings/pgvector once document volume makes structural filtering insufficient.
- Revisit OpenHands (+ optionally local Ollama models) specifically when/if a coding-focused subagent is added.
- Trial Hermes Agent + Hermes Desktop hands-on before wiring any real business workflow through it, given both are relatively new/fast-moving.
- Revisit commercialization/multi-tenancy only if real external demand appears — not a current design target.
