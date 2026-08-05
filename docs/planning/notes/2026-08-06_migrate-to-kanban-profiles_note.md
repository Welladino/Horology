# Implementation Note

## Topic
- migrate-to-kanban-profiles

## Context

The current subagent mechanism (`INDEX.md` lazy-load + `delegate_task` + `write_document` as the reliable output channel) works and was verified end-to-end earlier this session — GTM Manager produced a real, full-length recommendation (document id=5) despite `delegate_task`'s known output-truncation bug (NousResearch/hermes-agent#26425), by writing directly to the document graph instead of relying on the delegation return value.

Separately, while exploring Hermes's `kanban` and `profile` subcommands (prompted by noticing them in `hermes --help`), found that Hermes has a native mechanism for exactly the "one supervisor, many named specialist workers" pattern this project has wanted from the start — one that's more robust than what we built, but comes with real setup gotchas and deepens Hermes-specific lock-in. Investigated hands-on (not just from docs) before deciding: created a throwaway test profile, dispatched a real kanban task to it, and iterated through two real failures before getting a clean success.

## Decision

**Migrate GTM Manager and Marketing Executive from the `delegate_task`-based mechanism to Hermes kanban profiles.**

### What a "profile" gives that `delegate_task` doesn't

- A profile is a full, separate identity: its own `SOUL.md`, `.env`, `config.yaml` (including its own model/provider), skills, memory, and cron — not an ephemeral context stuffed into one function call.
- Persistent memory across tasks — a profile can accumulate its own experience over time, the way Second-Soul's own journal does. `delegate_task` subagents are reborn from scratch every single call, by design; they can never do this.
- Task results live as durable rows in `kanban.db` with a full event/comment history, inspectable via `hermes kanban show`/`list`/`log` at any time later. This is a fundamentally different, more durable channel than `delegate_task`'s return value — the truncation bug (found and worked around earlier this session) simply doesn't apply to it, because it isn't the same code path.
- Native parallel/coordination support via `hermes kanban swarm` (`--worker PROFILE:TITLE`, repeatable) and `hermes kanban link` (parent → child dependencies) — this is the built-in answer to "one supervisor dispatches to and combines results from multiple domain specialists," which was the original ask behind this whole project. Second-Soul stays the only agent the founder talks to; GTM Manager/Marketing Executive/future specialists become profiles Second-Soul assigns tasks to and reads results from — never something the founder interacts with directly.

### Real setup gotchas found during hands-on testing (not documented anywhere we found — learned by testing)

1. **A profile with no model configured fails silently to an unexpected fallback**, rather than inheriting the parent config's model or erroring clearly. Confirmed: a test profile with no `model:` set in `profile.yaml` was resolved to `z-ai/glm-5.2` (not our configured `deepseek/deepseek-v4-flash`), with no warning beyond a generic "no API keys yet" notice at profile-creation time. Every profile going forward must have its model explicitly set — never rely on inheritance.
2. **A worker that finishes without calling `kanban_complete` (or `kanban_block`) is treated as a "protocol violation" and silently retried** (up to `max-retries`, default 2 extra attempts) rather than failing clearly on the first miss. A persona that doesn't know it must call `kanban_complete` will loop through retries with no obvious signal why. Every subagent persona migrated to a profile must explicitly state this requirement.
3. Both gotchas were caught by running a real test task, not by reading documentation — the first attempt (before fixing either) produced two "protocol violation" runs and one outright crash before the actual root cause (an OpenRouter content-filter 403, a third, unrelated issue) was found and resolved.

### The Hermes lock-in tradeoff, named explicitly

`hermes kanban swarm`, `hermes kanban link`, the `kanban_complete` protocol, and the profile-as-worker dispatch model are all Hermes-specific mechanics — not a general MCP capability, not portable to Claude Agent SDK, OpenHands, or any other platform. This deepens the Hermes-specific investment already made (per the founding-decisions note's choice of Hermes over Claude Code CLI for usage-bucket isolation) more than anything built so far — the personas-as-markdown-files pattern, the document-graph MCP server, and the Neon schema are all portable to a different orchestrator later with comparatively little rework; kanban's task-dispatch mechanics are not. Decided this tradeoff is acceptable given Hermes is already the committed platform for automated runs, and the reliability/coordination gain is worth it.

## Rationale

The `write_document`-as-output-channel workaround was a legitimate fix for the specific symptom (truncated output), but it left the underlying mechanism (`delegate_task`) as the actual delegation/coordination path, including its ephemeral-subagent limitation and its native inability to express "one task depends on several others" without extra bookkeeping. Kanban fixes the root cause, not just the symptom, and directly implements the coordination pattern (supervisor → multiple named domain specialists → combined result) that has been the goal since the very first message of this whole project. The gotchas are real and cost real time to find, but they're one-time setup knowledge now captured here, not a recurring cost.

## Impact

- `personas/subagents/gtm-manager.md` and `personas/subagents/marketing-executive.md` need to become real Hermes profiles (own `SOUL.md`, explicit model config), not files read and injected into `delegate_task`'s `context`.
- `personas/subagents/INDEX.md`'s lazy-load pattern may still be useful as a human/repo-level index of what profiles exist, but Second-Soul's own dispatch logic in `SOUL.md` needs to change from "read persona file, call delegate_task" to "create/assign a kanban task to the right profile."
- The `write_document`-as-reliable-output-channel instruction in each subagent persona stays useful regardless (documents are still the right place for real business artifacts), but is no longer compensating for a broken return path — kanban's own task/comment history is durable on its own.
**Completed 2026-08-06.** Both profiles created (`gtm-manager`, `marketing-executive`) with explicit model config (`deepseek/deepseek-v4-flash` via OpenRouter — learned the hard way that the model belongs in the profile's `config.yaml`, not `profile.yaml`, which only holds metadata like `description`), persona content synced to each profile's own `SOUL.md`, and the document-graph MCP server connected per-profile (MCP connections are not shared across profiles — each needed its own `hermes -p <profile> mcp add`). Second-Soul's `SOUL.md` rewritten to create/dispatch/check kanban tasks instead of calling `delegate_task`.

Re-verified end-to-end with the same real business question used in the original truncation-bug report: Second-Soul created and dispatched a kanban task to `gtm-manager`, which completed cleanly (`hermes kanban list` showed `done`, single run, no protocol violations) and wrote a full recommendation to the document graph — confirmed directly via DB query: document id=6, 7,820 characters of content, `created_by_agent='gtm-manager'`.

## Follow-Ups

- Decide whether `hermes kanban dispatch` needs to run continuously (a daemon/gateway-integrated mode) rather than being invoked manually, for this to work under the twice-daily cron pattern this whole project is built around — not yet investigated. Manual dispatch was used for all testing so far.
- `marketing-executive` profile is configured and connected but not yet exercised with a real task — only `gtm-manager` has been verified end-to-end post-migration.
- Consider whether kanban's own task/comment history makes the `run_log` table (in the document graph schema, not yet used) partially redundant, or whether they serve genuinely different purposes worth keeping both.
