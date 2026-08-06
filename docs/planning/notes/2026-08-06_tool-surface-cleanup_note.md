# Implementation Note

## Topic
- tool-surface-cleanup

## Context

Reviewed the full tool inventory across all four profiles (Second-Soul + three subagents) after adding the `max_web_searches` cap, to answer: which tools are enabled, and which are actually capped. Found that beyond `max_web_searches`, almost nothing has a native per-tool call limit — `agent.max_turns` (the overall iteration ceiling) is the only other real backstop.

## Decision

**Disabled `browser`, `terminal`, and `code_execution`** on Second-Soul (the default profile — the three subagents already had `terminal`/`code_execution` disabled from the earlier hardening pass, so only `browser` was new for them):
- **`terminal`**: real, unsandboxed command execution on the local backend (confirmed earlier this session — shares the container's kernel, only secret-shaped env vars stripped). No part of Second-Soul's actual workflow (reading the index, dispatching kanban tasks, checking status, calling the two MCP servers, managing its own journal) requires shell access.
- **`code_execution`**: the document-graph and github-monitor MCP servers were built specifically so agents never need arbitrary code execution to interact with Postgres or GitHub. Nothing in the current design calls for it.
- **`browser`**: full page navigation/JS execution — a materially larger surface than `web_search`/`web_extract`, and nothing currently requires it over plain search/extract.

**`web_extract` left uncapped, deliberately, not as an oversight.** Tested whether an equivalent to `max_web_searches` exists for extract (`tool_loop_guardrails.loop_caps.max_web_extracts`) — Hermes's `config set` flagged it as an unrecognized key. Per the earlier `hardening-config-options` research, `loop_caps` only supports two hardcoded names (`max_web_searches`, `max_subagents`); there's no general per-tool cap mechanism.

**No soft (persona-instructed, unenforced) caps added to compensate.** A prompt telling a subagent "don't call X more than N times" is not a real limit — it's a suggestion the agent can ignore or forget under context pressure, and this project has a working principle of preferring real enforcement over trusting agent compliance (the same reasoning behind rejecting `delegate_task`'s lack of per-subagent tool restriction, and behind the original code-execution-vs-MCP decision). Left as a known, accepted gap rather than papered over.

## Rationale

Same principle applied throughout this project: narrowest justified capability per identity. `terminal`/`code_execution`/`browser` were carried over from Hermes's default profile template without being individually justified against actual usage — this pass closes that gap. The `web_extract` cap gap is real but not worth a fake fix; documenting it clearly is more honest than a soft instruction that looks like a safeguard but isn't one.

## Impact

- Full current tool/cap inventory is now documented in [`docs/architecture/system_overview.md`](../../architecture/system_overview.md) ("Toolset and caps" section) — the place to check before adding a new tool or reasoning about what a compromised/misbehaving profile could actually do.
- Any future subagent's setup checklist (`docs/runbook/docker/hermes_setup.md`) now disables `browser` by default alongside the toolsets already on that list, and sets `max_web_searches` at creation time rather than as a follow-up step.

## Follow-Ups

- If Hermes ever adds a general per-tool cap mechanism (not just the two hardcoded `loop_caps` names), revisit `web_extract` and the two MCP servers' tools for real caps instead of leaving them uncapped.
- If a future subagent role genuinely needs `browser`, `terminal`, or `code_execution`, enable it deliberately for that one profile with a documented reason — don't restore it broadly.
