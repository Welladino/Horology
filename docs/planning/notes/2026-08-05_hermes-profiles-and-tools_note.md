# Hermes personas, skills and tools

## Topic
- hermes-profiles-and-tools

## Context

Setting up Second-Soul and its first subagents (2026-08-05 to 08-06) raised three questions: where personas live and how they reach the agent, how to keep the supervisor's prompt from growing with every subagent, and which skills and tools each profile actually needs. Hermes' docs were checked before designing, because the original plan assumed a native named-persona system like Claude Code's `.claude/agents/`.

## Decisions

**Personas live in the repository (2026-08-05).** Hermes' only delegation primitive at the time, `delegate_task`, is stateless: the parent passes `goal` and `context`, and the subagent inherits the parent's toolsets minus a fixed blocklist. There was no registry of named agent types ([NousResearch/hermes-agent#9459](https://github.com/NousResearch/hermes-agent/issues/9459) was open). So each persona became a versioned file under `personas/`, written like a system prompt. Kanban profiles later replaced `delegate_task` ([dispatch note](2026-08-05_hermes-kanban-dispatch_note.md)), but the files stayed the source of truth, synced into `hermes-data/`.

**Index first, full persona on demand (2026-08-05).** `SOUL.md` is sent with every message, so describing each subagent inside it would grow every conversation's cost. `personas/subagents/INDEX.md` now lists name, one-line scope and path; Second-Soul reads it first and loads a full persona only after choosing one. Adding a subagent means one index line plus one file; `SOUL.md` doesn't change. This mirrors Hermes' own skills catalog. A live test found that the agent's file-tool working directory is `/opt/hermes`, not the mounted `/opt/data`, so the first relative path failed; every persona reference now uses the absolute `/opt/data/...` path.

**Skills scoped per profile (2026-08-06).** New profiles inherited all 71 bundled skills (`python-debugpy`, `computer-use`, `comfyui` and so on). Profiles, unlike `delegate_task`, can be scoped. `gtm-manager` was opted out (`hermes -p gtm-manager skills opt-out --remove --yes`) and given back only `arxiv`, `grounded-citations` and `blogwatcher`, copied from `hermes-data/skills/research/` because `hermes skills repair-official` doesn't restore bundled skills. `marketing-executive` has none. MCP connections are separate from skills and were unaffected.

**Unused tools off (2026-08-06).** `terminal` (unsandboxed, shares the container kernel), `code_execution` and `browser` were disabled on every profile; nothing in the workflow needs them, and the MCP servers exist so agents never need arbitrary code to reach a database or API. `web_search` is capped at 10 per turn. `web_extract` stays uncapped deliberately: `loop_caps` accepts only `max_web_searches` and `max_subagents`, and `config set` rejects `max_web_extracts`. No persona-level "soft caps" were added: an instruction an agent can ignore under context pressure is not a limit, and this project prefers real enforcement to trusting compliance.

**Monitoring and the Hermes MCP bridge (planned 2026-08-05).** GitHub, Neon and GCP monitoring were to follow one pattern: a plain script fetches on a `no_agent=True` cron and calls the model only when something needs judgment, with read-only, least-privilege credentials (a fine-grained read-only GitHub PAT, `roles/logging.viewer` for GCP). GitHub monitoring was built as a separate MCP server, later folded into the gateway and then removed ([gateway provider scope note](2026-10-12_gateway-provider-scope_note.md)). Hermes can also serve MCP over stdio (`docker exec -i horology-hermes hermes mcp serve`) so a Claude Code session elsewhere could inspect it; this was never wired up.

## Rationale

Narrowest justified capability per identity, applied wherever the platform can enforce it. Checking Hermes' real API first avoided designing against a feature that didn't exist, and testing paths live caught a working-directory bug that would have silently broken delegation.

## Impact

- New subagent profiles start with no bundled skills, `terminal`, `code_execution` and `browser` off, and `max_web_searches` set; skills are added one at a time with a reason. Checklist: [Hermes setup](../../runbook/docker/hermes_setup.md).
- The current tool and limit inventory is in [Hermes architecture](../../architecture/hermes/README.md#tools-and-limits).

## Follow-Ups

- Second-Soul (the default profile) still has the full bundled skill set.
- If Hermes adds a general per-tool cap, revisit `web_extract` and MCP tools.
- Neon and GCP monitoring by script-only cron is still not built.
- If a role genuinely needs `browser`, `terminal` or `code_execution`, enable it for that one profile with a documented reason.
