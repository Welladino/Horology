# Research Brief

## Topic
- kanban-timeout-signaling

## Question
- When lowering `agent.max_turns` on subagent profiles, is there any structured, queryable signal when a kanban task runs out of its turn budget before finishing — or only a CLI-visible warning string with nothing machine-readable to detect it in an automated context?

## Summary
- Initial doc research claimed no structured event exists for turn-budget exhaustion, specific to kanban or otherwise.
- That was wrong. A real test showed kanban produces a proper `timed_out` event, distinct from `protocol_violation` and `completed`, with a clear machine-readable reason.

## Sources
- WebFetch against Hermes's configuration docs (first pass — produced the incorrect "no structured signal" claim).
- Direct hands-on test: a throwaway profile with `agent.max_turns: 2`, given a kanban task requiring more tool calls than that budget allows, dispatched, and the resulting event log inspected directly.

## Findings
- Doc research claimed: no specialized event type for max-turns exhaustion, kanban-specific or otherwise; only a CLI-facing warning message (`⚠ Iteration budget reached (N/N) — response may be incomplete`); no session field marking "incomplete due to budget."
- Real test contradicted this directly. Event log from the test task showed:
  ```
  [run 7] timed_out {'error': 'Iteration budget exhausted (2/2) — task could not complete within the allowed iterations', 'failures': 1}
  ```
  This is a distinct, structured event type — queryable via `hermes kanban show <task_id>` like any other event — separate from `protocol_violation` (task stopped without calling `kanban_complete`/`kanban_block`) and `completed`. Task status returns to `ready` for retry, not silently lost.
- This is the second time this session doc research (or a first-pass WebFetch) produced a materially wrong answer that a cheap, direct hands-on test corrected — the same pattern as the `fallback_model` key-name confusion and the `profile.yaml`/`config.yaml` mixup found earlier.

## Recommendation
- Trust `hermes kanban show`'s actual event log over doc-research claims about what signals exist — verify hands-on whenever a claim is cheap to test and the design will depend on it.
- Build turn-budget handling around the confirmed `timed_out` event: Second-Soul can distinguish it from `protocol_violation`/`completed` and act accordingly (re-scope/split vs. retry vs. treat as healthy).
- Additionally, have subagent personas proactively call `kanban_block` with a reason if they sense they're running low, since a bare `timed_out` event (while now confirmed structured) doesn't explain *why* the task was too big — a deliberate block is more actionable for Second-Soul than an unexplained timeout.

## Open Questions
- None outstanding for this specific question — resolved and implemented.
