# Hermes dispatch: from delegate_task to kanban profiles

## Topic
- hermes-kanban-dispatch

## Context

The first end-to-end delegation test (2026-08-05, Second-Soul → GTM Manager, a real first-channel GTM question) worked mechanically: the right subagent was chosen and its persona and business context were injected. But the answer that reached Second-Soul was cut to about 100 characters (`...+94 chars` in the raw log) on three attempts. Second-Soul behaved correctly: it told the founder the pipeline was truncating output and did not invent a clean answer.

This is a known, open upstream bug in Hermes Agent:

- [NousResearch/hermes-agent#26425](https://github.com/NousResearch/hermes-agent/issues/26425): responses truncated by the output length limit, reopened after an earlier fix.
- [NousResearch/hermes-agent#70294](https://github.com/NousResearch/hermes-agent/issues/70294): in cron jobs, top-level `delegate_task` results are dropped silently while the job reports `ok`. Worse than the interactive case, and it hits exactly the unattended pattern Horology is built around.

## Decisions

**1. Route output through the document graph (2026-08-06).** Once the document-graph MCP server was connected to Hermes (HTTP on the internal Docker network, no host port; registered with `hermes mcp add document-graph --url http://document-graph-mcp:8765/mcp`), every persona was changed so subagents write their full answer with `write_document` and report back only a pointer; Second-Soul reads the real content with `get_document`. Retesting the same question produced document 5 (`recommendation`, `gtm-manager`) with 7,875 characters, checked directly in the database rather than trusted from the agent's report. An earlier "verification" through a polling script had given a false positive because of a bug in the script, caught only by cross-checking the session transcript and the database.

**2. Replace delegate_task with kanban profiles (2026-08-06).** Tradeoffs are in the [research brief](../research/2026-08-06_delegate-task-vs-kanban-profiles_research.md). `gtm-manager` and `marketing-executive` became Hermes profiles with their own `SOUL.md`, an explicit model in the profile's `config.yaml` (not `profile.yaml`, which holds only metadata), and their own document-graph connection (MCP connections are per profile: `hermes -p <profile> mcp add`). Second-Soul's persona now creates, dispatches and checks kanban tasks. The same real question was re-run: the task finished `done` in a single run with no protocol violations and wrote document 6 (7,820 characters, `created_by_agent='gtm-manager'`). Kanban fixes truncation at the root, because it is a different code path, and implements the supervisor → named specialists pattern the project wanted from the start.

**3. Turn budgets with a visible timeout (2026-08-06).** Following the hardening audit's `agent.max_turns` finding, both subagent profiles were set to 50 turns with `hermes -p <profile> config set agent.max_turns 50` (direct edits to `config.yaml` are reverted by the running process). The docs said there was no structured timeout signal; a real test found a `timed_out` kanban event ([research](../research/2026-08-06_kanban-timeout-signaling_research.md)). Subagent personas now know their budget and call `kanban_block` with a reason, after saving any usable partial output, when they won't finish. Second-Soul's persona tells apart `done`, `protocol_violation` and `timed_out`, and considers splitting a task after an unexplained `timed_out`. A live query confirmed `gtm-manager` could describe its budget and the block procedure. Hermes has no token or cost cap; that is set on the OpenRouter dashboard instead.

## Rationale

Getting real subagent output back to the supervisor, reliably and unattended, is what the whole design depends on. Surfacing the bug with two subagents and one test question was far cheaper than finding it after cron jobs and more profiles relied on the broken path. Kanban also gives each subagent a persistent identity and a durable, queryable task history.

## Impact

- `delegate_task` is no longer used for dispatch; personas in `personas/subagents/` are real profiles, and `INDEX.md` remains the lookup Second-Soul reads first.
- Writing finished work to the document graph stays the rule, now as the right home for business artifacts rather than a workaround.
- Every task has a 50-turn budget and a defined, queryable failure mode.

## Follow-Ups

- Decide whether `hermes kanban dispatch` must run continuously for scheduled runs; all testing so far used manual dispatch.
- Decide whether kanban history makes the unused `run_log` table redundant.
- A `timed_out` without a prior `kanban_block` means the task was under-scoped when created, not only a budget problem.
- Second-Soul's own limit was later set to 150 turns (see [Hermes architecture](../../architecture/hermes/README.md#tools-and-limits)).
