# Research Brief

## Topic
- horology-founding-options

## Question
- Solo founder building the Article Aggregator SaaS with no co-founder. Wanted a personal "AI co-founder" — a supervisor agent dispatching to specialist subagents (GTM manager, marketing executive, DB engineer, DevOps, sourcing, strategy, etc.) for the non-engineering side of running the business. What's the right way to build this: which orchestration layer, which execution platform, how should generated documents be stored, and should this be designed for eventual commercialization?

## Summary
- No third-party orchestration framework (LangChain/CrewAI/AutoGen/etc.) is needed — Claude Code, Codex, Google ADK, and Hermes Agent all already ship native supervisor-dispatches-to-subagents orchestration.
- Hermes Agent (Nous Research) was chosen over Claude Code/Codex CLI for the automated/scheduled runs specifically because Claude Code's usage bucket is shared with interactive coding work — scheduled automation would compete with and risk starving actual coding capacity.
- Generated business documents belong in their own store (a separate Postgres project, MCP-reachable), kept structurally separate from Horology's own build-planning docs and from whichever orchestrator is running.
- Commercialization was explicitly not designed for — "AI co-founder" is already a funded, marketed category with a thin moat; better to keep the boundary clean (own DB, own thin API surface) so a retrofit is possible later without designing for it now.

## Sources
- Prior conversation history mapping options across Claude Code, Codex, Google ADK, Hermes Agent, OpenHands, LangChain/LangGraph, CrewAI, Temporal, Obsidian, MiniMax/MaxHermes.
- Claude Code usage-limit documentation (shared bucket across Claude Code, Claude.ai chat, Cowork).
- Hermes Agent feature set: model-agnostic (200+ backends via OpenRouter), native cron with script-only `no_agent=True` mode, MCP support, multi-platform messaging, Hermes Desktop GUI (public preview, June 2026).
- `Article_aggregator_agent`'s own `similarity.py`/`gemini_embed.py` (~100 lines combined) as the reference point for "would reuse be cheap or costly" on embeddings.

## Findings
- **Orchestration framework**: unnecessary. A third-party framework only earns its place for a hand-authored deterministic control-flow graph, or genuinely mixing multiple vendors' agents in one orchestration — neither applied here.
- **Durable execution (Temporal)**: a heavier, more general layer (survives crashes/long waits for arbitrary code) than needed at this scale. Worth revisiting only if multi-day human-wait reliability becomes a real requirement.
- **Obsidian**: no logic value — not agent-queryable, not structurally relational, pure human-readable sugar not needed yet.
- **Embeddings/pgvector**: not needed yet — structural filtering (by type/date/tag) is sufficient at Horology's expected document volume. If needed later, a small standalone embeddings wrapper is cheaper to write (~100 lines) than importing/coupling to `Article_aggregator_agent`'s embedding code, which risks entangling two services that may end up in different GCP projects.
- **Execution platform (Hermes vs. Claude Code/Codex CLI)**: Hermes fits better — general-purpose (not coding-specific like OpenHands), model-agnostic, native multi-agent pattern, native cron with a cheap script-only mode for watchdogs, MCP support, multi-platform messaging, and a GUI option. Estimated cost via OpenRouter with a cheap model: ~$1-15/month, on a budget fully separate from Claude Code's coding-limit bucket. Caveat: Hermes and Hermes Desktop are both new/fast-moving — worth a hands-on trial before relying on them for real business workflows.
- **OpenHands**: evaluated and set aside — it's coding-agent-first, and Horology's subagent roster is mostly non-coding roles. Flagged as a good fit specifically for a future coding-focused subagent, especially paired with a local model via Ollama for near-zero-marginal-cost mechanical tasks.
- **Document storage**: business documents (GTM docs, marketing reports, findings) need to live somewhere MCP-reachable from any orchestrator, separate from Horology's own build-planning docs (which stay human-authored, git-versioned, in this repo). A shared store also solves the multi-repo context problem — plain per-repo local files can't be queried across repos/projects.
- **Commercialization**: "AI co-founder" is already a funded, marketed commercial category (e.g. Tanka, ai.com) — productizing this would mean competing with well-resourced players on prompts + orchestration alone, a thin moat, unlike the actual product's real differentiation (sourced/curated content + delivery pipeline).

## Recommendation
- Build as its own project (Horology), own repo, own database — not inside `Article_aggregator_agent`, no shared code or DB, specifically so a future multi-tenant/microservice split doesn't require untangling shared dependencies.
- Use Hermes Agent as the execution platform for automated/scheduled runs; keep Claude Code/Codex for interactive coding work and for personally driving the system by hand.
- Store generated documents in a schema separate from build-planning docs: `documents` (with a `supersedes_id` self-FK for version chains), `document_links` (relation edges), `run_log` (audit trail) — reached via MCP so it's orchestrator-agnostic.
- Do not design for commercialization now; keep the DB/API boundary clean so a retrofit stays possible without current design overhead.
- If this harness is ever reused for full-time-job tasks, treat it as a second, fully separate deployment (separate DB, keys, cron) — never sharing data with the business instance, and only after explicit employer sign-off.

## Open Questions
- Whether Hermes/Hermes Desktop prove reliable enough in practice for real business workflows (resolved via hands-on trial in a later note).
- Whether/when embeddings become necessary as document volume grows.
- Whether commercialization ever becomes a real consideration (currently deferred indefinitely).
