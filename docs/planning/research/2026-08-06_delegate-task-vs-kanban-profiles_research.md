# Research Brief

## Topic
- delegate-task-vs-kanban-profiles

## Question
- The existing subagent mechanism (`INDEX.md` lazy-load + `delegate_task` + `write_document` as the reliable output channel) works and was verified end-to-end — GTM Manager produced a real, full-length recommendation despite `delegate_task`'s known output-truncation bug (NousResearch/hermes-agent#26425), by writing directly to the document graph instead of relying on the delegation return value. Separately, exploring Hermes's `kanban` and `profile` subcommands surfaced what looked like a more native mechanism for "one supervisor, many named specialist workers." Is it actually better, and is the setup/lock-in cost worth it?

## Summary
- Kanban + profiles is a real, more robust native mechanism — genuine separate identities with persistent memory, durable task history, and native parallel/coordination support (`hermes kanban swarm`, `hermes kanban link`).
- It fixes the `delegate_task` truncation bug at the root (different code path entirely) rather than working around the symptom.
- Comes with two real, undocumented setup gotchas, found only by testing, not by reading docs.
- Deepens Hermes-specific lock-in more than anything built so far — kanban's task-dispatch mechanics are not portable to another orchestrator, unlike the personas-as-markdown-files pattern or the document-graph MCP server.

## Sources
- Hands-on investigation: created a throwaway test profile (`test-worker`), dispatched a real kanban task to it, iterated through failures to reach a clean success.
- `hermes --help`, `hermes kanban --help`, `hermes profile --help`, `hermes profile create --help`.

## Findings

**What a profile gives that `delegate_task` doesn't:**
- A profile is a full, separate identity: its own `SOUL.md`, `.env`, `config.yaml` (model/provider), skills, memory, and cron — not an ephemeral context stuffed into one function call.
- Persistent memory across tasks — a profile can accumulate its own experience, the way Second-Soul's own journal does. `delegate_task` subagents are reborn from scratch every call, by design.
- Task results live as durable rows in `kanban.db` with a full event/comment history, inspectable via `hermes kanban show`/`list`/`log` at any time later — a fundamentally different, more durable channel than `delegate_task`'s return value. The truncation bug doesn't apply to it, because it isn't the same code path.
- Native parallel/coordination support via `hermes kanban swarm` (`--worker PROFILE:TITLE`, repeatable) and `hermes kanban link` (parent → child dependencies) — the built-in answer to "one supervisor dispatches to and combines results from multiple domain specialists," the original ask behind this whole project.

**Real setup gotchas found only by testing, not documented anywhere found:**
1. A profile with no model configured fails silently to an unexpected fallback rather than inheriting the parent config's model or erroring clearly. Confirmed: a test profile with no `model:` set was resolved to `z-ai/glm-5.2` (not the configured `deepseek/deepseek-v4-flash`), with no warning beyond a generic "no API keys yet" notice at profile-creation time.
2. A worker that finishes without calling `kanban_complete` (or `kanban_block`) is treated as a "protocol violation" and silently retried (up to `max-retries`, default 2 extra attempts) rather than failing clearly on the first miss. A persona unaware of this requirement loops through retries with no obvious signal why.
3. Both were caught only by running a real test task — the first attempt (before fixing either) produced two "protocol violation" runs and one outright crash (traced to an unrelated OpenRouter content-filter 403) before reaching a clean success.

**The Hermes lock-in tradeoff:** `hermes kanban swarm`, `hermes kanban link`, the `kanban_complete` protocol, and the profile-as-worker dispatch model are all Hermes-specific mechanics — not a general MCP capability, not portable to Claude Agent SDK, OpenHands, or any other platform. This deepens Hermes-specific investment more than anything built so far — the personas-as-markdown-files pattern, the document-graph MCP server, and the Neon schema are all portable to a different orchestrator later with comparatively little rework; kanban's task-dispatch mechanics are not.

## Recommendation
- Migrate GTM Manager and Marketing Executive from `delegate_task` to real kanban profiles. The `write_document`-as-output-channel workaround was a legitimate fix for the specific symptom (truncated output), but left `delegate_task` as the actual delegation/coordination path, including its ephemeral-subagent limitation and native inability to express task dependencies. Kanban fixes the root cause and directly implements the coordination pattern this project has wanted from the start.
- Accept the deepened Hermes lock-in — Hermes is already the committed platform for automated runs (per the founding-decisions research), and the reliability/coordination gain is worth it.
- Every future profile must have its model explicitly set (never rely on inheritance) and every subagent persona must explicitly state the `kanban_complete`/`kanban_block` requirement.

## Open Questions
- Whether `hermes kanban dispatch` needs to run continuously (a daemon/gateway-integrated mode) for the twice-daily cron pattern this project is built around — not yet investigated at the time of this brief.
- Whether kanban's own task/comment history makes the `run_log` table (in the document graph schema) partially redundant.
