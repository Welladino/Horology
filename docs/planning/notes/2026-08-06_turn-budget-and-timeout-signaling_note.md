# Implementation Note

## Topic
- turn-budget-and-timeout-signaling

## Context

Followed up on the hardening audit's `agent.max_turns` finding (default 500, our config had it at 150) with two concrete requests: lower it to 50 on the subagent profiles, and get some signal when a task can't finish in that budget rather than a silent cutoff.

Initial doc research (via WebFetch) claimed **no structured event exists** for max_turns exhaustion — only a CLI-visible warning string, nothing machine-readable, nothing kanban-specific. Decided to verify this hands-on before designing around it, given how often doc research has been wrong or stale this session (the `fallback_model` key-name confusion, the profile.yaml/config.yaml mixup).

## Decision

**The doc research was wrong. Kanban has a real, structured `timed_out` event, distinct from `protocol_violation` and `completed`.**

Verified via a real test: created a throwaway profile with `agent.max_turns: 2`, gave it a kanban task requiring several tool calls (three separate web-search-and-summarize steps), dispatched it, and confirmed the actual event log:
```
[run 7] timed_out {'error': 'Iteration budget exhausted (2/2) — task could not complete within the allowed iterations', 'failures': 1}
```
This is queryable via `hermes kanban show <task_id>` like any other event, and status becomes `ready` again for retry (not silently lost). Cleaned up the test profile and task afterward.

**Set `agent.max_turns: 50`** on both `gtm-manager` and `marketing-executive` profiles via `hermes -p <profile> config set agent.max_turns 50` (not a direct file edit — learned earlier this session that editing `config.yaml` on disk while Hermes is running gets silently reverted by the live process).

**Updated both subagent personas** to know their turn budget and to proactively call `kanban_block` with a clear reason if they sense they won't finish in time — writing any usable partial output via `write_document` first rather than losing it. Rationale given to them: a deliberate block carries a reason; an exhausted budget's `timed_out` event, while now confirmed structured, doesn't explain *why* the task was too big — proactive blocking is more informative for Second-Soul to act on (e.g., decide to split the task).

**Updated Second-Soul's own persona** to distinguish the three outcomes when checking on a dispatched task (`done`/`completed`, `protocol_violation`, `timed_out`) rather than treating anything non-`done` as the same generic failure, and to consider splitting a task into smaller kanban tasks if it sees an unexplained `timed_out` (no prior `kanban_block` with a reason).

Verified the updated persona took effect via a live query — `gtm-manager` correctly described its turn budget and the block-proactively procedure in its own words.

**Token/cost cap (the founder's other item):** confirmed no equivalent exists in Hermes itself — being set directly on the OpenRouter account dashboard instead, outside this project's config.

## Rationale

This is the second time this session that verifying a claim hands-on (rather than trusting either documentation or a first-pass research agent) produced a materially different, better answer than the initial finding — worth continuing to default to a real test when a claim is easy to verify cheaply, especially for anything the design will depend on.

## Impact

- Subagent tasks now have a real budget (50 turns) with a defined, queryable failure mode instead of running unboundedly or failing silently.
- Second-Soul can now make a better decision when a subagent doesn't finish (re-scope/split vs. just retry) instead of treating all non-completions the same.

## Follow-Ups

- Consider whether Second-Soul's own `agent.max_turns` (currently the Hermes default, not explicitly set) should also be bounded — not addressed in this pass, since Second-Soul's own interactive/scheduled-run behavior wasn't the focus here.
- If a real task later hits `timed_out` without a prior deliberate `kanban_block`, treat that as a signal the task was under-scoped when created, not just a budget-tuning problem.
