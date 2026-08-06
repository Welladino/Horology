# Implementation Note

## Topic
- turn-budget-and-timeout-signaling

## Context

Followed up on the hardening audit's `agent.max_turns` finding (default 500, our config had it at 150) with two concrete requests: lower it to 50 on the subagent profiles, and get some signal when a task can't finish in that budget rather than a silent cutoff. Investigation into whether a structured signal exists (doc research was wrong; a real test found the `timed_out` event) is in [`docs/planning/research/2026-08-06_kanban-timeout-signaling_research.md`](../research/2026-08-06_kanban-timeout-signaling_research.md).

## Decision

**Set `agent.max_turns: 50`** on both `gtm-manager` and `marketing-executive` profiles via `hermes -p <profile> config set agent.max_turns 50` (CLI command, not a direct file edit — editing `config.yaml` on disk while Hermes is running gets silently reverted by the live process).

**Updated both subagent personas** to know their turn budget and to proactively call `kanban_block` with a clear reason if they sense they won't finish in time — writing any usable partial output via `write_document` first rather than losing it.

**Updated Second-Soul's own persona** to distinguish the three outcomes when checking on a dispatched task (`done`/`completed`, `protocol_violation`, `timed_out`) rather than treating anything non-`done` as the same generic failure, and to consider splitting a task into smaller kanban tasks if it sees an unexplained `timed_out` (no prior `kanban_block` with a reason).

Verified the updated persona took effect via a live query — `gtm-manager` correctly described its turn budget and the block-proactively procedure in its own words.

**Token/cost cap (the founder's other item):** confirmed no equivalent exists in Hermes itself — being set directly on the OpenRouter account dashboard instead, outside this project's config.

## Rationale

Second-Soul now has a defined, structured way to distinguish "the subagent finished," "the subagent is misconfigured," and "the task was too big for its budget" — see the research brief for how the `timed_out` event was confirmed to exist and be queryable.

## Impact

- Subagent tasks now have a real budget (50 turns) with a defined, queryable failure mode instead of running unboundedly or failing silently.
- Second-Soul can now make a better decision when a subagent doesn't finish (re-scope/split vs. just retry) instead of treating all non-completions the same.

## Follow-Ups

- Consider whether Second-Soul's own `agent.max_turns` (currently the Hermes default, not explicitly set) should also be bounded — not addressed in this pass, since Second-Soul's own interactive/scheduled-run behavior wasn't the focus here.
- If a real task later hits `timed_out` without a prior deliberate `kanban_block`, treat that as a signal the task was under-scoped when created, not just a budget-tuning problem.
