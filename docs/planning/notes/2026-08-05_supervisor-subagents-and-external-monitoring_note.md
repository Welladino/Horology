# Implementation Note

## Topic
- supervisor-subagents-and-external-monitoring

## Context

Working through five practical setup questions: (a) how to create the supervisor + subagent personas, (b) whether/how to connect GitHub for code monitoring, (c) DB log monitoring, (d) GCP log monitoring, (e) how Claude (working in the `Article_aggregator_agent` repo) can reach into this Hermes instance via MCP.

Investigated Hermes's actual delegation mechanism (`delegate_task`) via its docs before designing anything, since the original plan assumed a `.claude/agents/*.md`-style named-persona system would exist natively.

## Decision

**(a) Subagent personas — Hermes has no native named-persona system; we build one in the repo**

`delegate_task` (Hermes's only delegation primitive) is generic and stateless: parent passes `goal` + `context` (freeform text), subagent gets a fresh context with zero persona beyond what's stuffed into those two fields. No per-subagent tool restriction (subagents inherit all of the parent's enabled toolsets, minus a fixed blocklist: `delegate_task`, `clarify`, `memory`, `send_message`, `cronjob`). No built-in registry of reusable named agent types (a "profiles for delegate_task" feature is an open, unimplemented GitHub issue — NousResearch/hermes-agent#9459 — as of this writing).

Workaround, treated as the actual design rather than a stopgap:
- Each subagent persona is a real markdown file in this repo, e.g. `personas/gtm-manager.md`, `personas/marketing-executive.md` — persona, scope, guardrails, written like a system prompt.
- The supervisor's own identity (`SOUL.md`, or a skill) is instructed to read the relevant persona file and pass its full contents as the `context` (or folded into `goal`) when calling `delegate_task` for that role.
- This makes personas durable and versioned in git even though Hermes's own delegation is stateless per-call — we're layering identity on top of a primitive that doesn't have it natively.
- Consequence: since subagents can't have their own restricted toolset, tool-scoping discipline has to be enforced by what the *supervisor* is told to only delegate for that purpose, and by what's globally enabled — not by a hard per-subagent boundary. Worth remembering this is softer than Claude Code's per-subagent tool allowlist.

**(b) GitHub for code monitoring — scoped to signal-watching, not open-ended code reading**

Decision: connect GitHub, but scope tightly to what's actually needed (CI status, security advisories, PR/issue signals for a DevOps-type subagent) rather than general repo browsing/reasoning over source.
- Use a GitHub **Fine-Grained Personal Access Token**, scoped to specific repo(s) only, **read-only** permissions (Contents/Issues/PRs/Actions: read; nothing write-capable).
- Route the token through iron-proxy (same mechanism verified working for the OpenRouter key) so the raw PAT is never held in the agent's own context.
- Prefer the `no_agent=True` script-only cron pattern (see founding-decisions note) for the mechanical polling; only escalate to an LLM call when something needs judgment ("is this CI failure/security advisory worth flagging").
- Incidental benefit: resolves the `doctor`-flagged missing `GITHUB_TOKEN` (currently rate-limited to 60 req/hr for Skills Hub).

**(c) DB log monitoring (Neon) and (d) GCP log monitoring — same script-only cron pattern**

Both are mechanical-fetch-plus-conditional-judgment jobs, same shape as the DB-engineer/DevOps roster item from the founding-decisions note:
- A plain script (not the LLM) does the fetch — Neon's own metrics/logs API for (c), `gcloud logging read` for (d) — and only pipes output to the agent when a threshold/anomaly condition is met, via `no_agent=True` cron.
- (d) specifically needs a GCP **service account scoped to least privilege** (e.g. `roles/logging.viewer`, not `Editor`/`Owner`), key handled through iron-proxy if used as an API credential, or mounted read-only into the container if a service-account JSON key is unavoidable.

**(e) MCP bridge from Claude/NLE repo to this Hermes instance**

Hermes can expose itself as an MCP server: `hermes mcp serve` (stdio transport, no host/port flags). Since Hermes runs inside Docker here, the invocation Claude Code needs to spawn is:

```
docker exec -i horology-hermes hermes mcp serve
```

registered in `Article_aggregator_agent`'s `.mcp.json` (or via `claude mcp add`) as a stdio-transport MCP server. This lets a Claude Code session working in the NLE repo reach into this running Hermes instance directly (e.g., inspect what the supervisor is doing) without switching contexts. Not yet wired up — next step.

## Rationale

Investigating Hermes's actual delegation API before designing (a) avoided building against a feature (native named subagent profiles) that doesn't exist yet. The repo-file-plus-context-injection workaround keeps the "personas live in git, not just in `hermes-data/`" principle already established, and is a reasonable enough approximation of the original design that it doesn't require revisiting the Hermes-over-Claude-Code decision. For (b)/(c)/(d), reusing the existing `no_agent=True` script-only cron pattern (rather than inventing something new) keeps cost down and keeps the LLM only in the loop where judgment is actually needed.

## Impact

- Subagent tool-scoping is softer than originally assumed (no hard per-subagent allowlist) — worth keeping in mind once real subagents are built; may need supervisor-level discipline/prompting to compensate.
- GitHub/DB/GCP monitoring all funnel through the same iron-proxy + script-only-cron pattern — consistent, and each new credential added gets the same egress protection already verified for OpenRouter.
- Sets up the MCP bridge as the way Claude (in the NLE repo, or anywhere else) can inspect/drive this Hermes instance going forward.

## Follow-Ups

- If NousResearch/hermes-agent#9459 (native agent profiles for `delegate_task`) ships, revisit whether to migrate off the repo-file-context-injection workaround onto the native mechanism.
- Decide GitHub monitoring scope precisely (which repo(s), which signals) before minting the PAT — not yet decided, just the access pattern.
- Neon DB not yet created — (c) is designed but not implemented.
- GCP service account for (d) not yet created — likely reuse/mirror the least-privilege patterns already documented in `Article_aggregator_agent`'s `docs/planning/notes/2026-07-20_trackD-D4d-phaseC-keyless-deployment-identities.md` and related G-track notes rather than reinventing GCP access design from scratch.
