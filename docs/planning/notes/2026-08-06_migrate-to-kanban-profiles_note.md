# Implementation Note

## Topic
- migrate-to-kanban-profiles

## Context

Investigation and tradeoff analysis (kanban+profiles vs. `delegate_task`, setup gotchas, Hermes lock-in cost) are in [`docs/planning/research/2026-08-06_delegate-task-vs-kanban-profiles_research.md`](../research/2026-08-06_delegate-task-vs-kanban-profiles_research.md). This note captures only the decision and what was actually implemented.

## Decision

**Migrated GTM Manager and Marketing Executive from the `delegate_task`-based mechanism to Hermes kanban profiles. Completed 2026-08-06.**

Both profiles created (`gtm-manager`, `marketing-executive`) with explicit model config (`deepseek/deepseek-v4-flash` via OpenRouter — learned the hard way that the model belongs in the profile's `config.yaml`, not `profile.yaml`, which only holds metadata like `description`), persona content synced to each profile's own `SOUL.md`, and the document-graph MCP server connected per-profile (MCP connections are not shared across profiles — each needed its own `hermes -p <profile> mcp add`). Second-Soul's `SOUL.md` rewritten to create/dispatch/check kanban tasks instead of calling `delegate_task`.

Re-verified end-to-end with the same real business question used in the original truncation-bug report: Second-Soul created and dispatched a kanban task to `gtm-manager`, which completed cleanly (`hermes kanban list` showed `done`, single run, no protocol violations) and wrote a full recommendation to the document graph — confirmed directly via DB query: document id=6, 7,820 characters of content, `created_by_agent='gtm-manager'`.

## Rationale

Kanban fixes the truncation bug at the root (a different code path from `delegate_task`, not a workaround) and directly implements the coordination pattern (supervisor → multiple named domain specialists → combined result) that has been the goal since the start of this project. See the research brief for the full pros/cons and the lock-in tradeoff accepted.

## Impact

- `personas/subagents/gtm-manager.md` and `personas/subagents/marketing-executive.md` are now real Hermes profiles (own `SOUL.md`, explicit model config), not files injected into `delegate_task`'s `context`.
- `personas/subagents/INDEX.md` remains useful as a human/repo-level index of what profiles exist; Second-Soul's dispatch logic now creates/assigns kanban tasks instead of calling `delegate_task`.
- The `write_document`-as-reliable-output-channel instruction in each subagent persona stays useful regardless (documents are still the right place for real business artifacts), but is no longer compensating for a broken return path — kanban's own task/comment history is durable on its own.

## Follow-Ups

- Decide whether `hermes kanban dispatch` needs to run continuously (a daemon/gateway-integrated mode) rather than being invoked manually, for this to work under the twice-daily cron pattern this project is built around — not yet investigated. Manual dispatch was used for all testing so far.
- Consider whether kanban's own task/comment history makes the `run_log` table (in the document graph schema, not yet used) partially redundant, or whether they serve genuinely different purposes worth keeping both.
