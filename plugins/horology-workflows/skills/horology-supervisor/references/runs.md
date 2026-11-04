# Runs

Runs are recorded in the execution history (Neon), through the document-graph connector. You make two calls per run: `claim_item` at the start and `finish_run` at the end. Specialists also call `reserve_id` for each new Decision or Document ID and `check_register_write` before each register write, passing the run ID. Everything else (status changes, outputs, decisions) is recorded from the sheets by the sync job, so don't report it.

## Claiming

Call `claim_item(pipeline_id, agent_type, run_location, kind)` once per item, before any work on it:

- `agent_type`: the claiming supervisor harness, Claude Code, Codex or Hermes. The packaged dispatch adapter gives its claim value; this can differ from the child Agent type (for example, a Codex supervisor dispatching ChatGPT Work). Hermes Coordinator does not claim; Operator is the claiming item harness and claims the item as Hermes in item mode.
- `run_location`: the adapter's effective location. This is normally the item's Run location (blank means Local); a cloud-only child uses Cloud without editing the row.
- `kind`: `run` for the supervisor, `plan` for the planner.

`claimed: true` returns a run ID (for example `R-12`) and a claim that expires in 2 hours. `claimed: false` means another live run holds the item: skip it and report the run ID it gives. An expired claim means a run died; the item can be claimed again.

If the connector isn't available, stop and say so. Never run an item without a claim.

## Finishing

Call `finish_run(run_id, status, skills_used, steps_done, notes, session_link)` once, at the end of every run you claimed:

| Field | Value |
|---|---|
| status | `done` (work finished and saved), `failed` (it couldn't finish) or `released` (you didn't start it) |
| skills_used | Specialist skills run, in order |
| steps_done | Which planned steps were completed, e.g. "1, 2" |
| notes | A few lines on the result or the blocker; the planner puts the old Next step wording here |
| session_link | The session URL or ID, when known |

## Steps

The planner, or a Stage 1 run on either route that finds no open rows, writes an item's steps on the Pipeline's **Steps** tab, one row per step: Pipeline ID, Step, Task, Specialist (optional) and Status (Planned, Done or Skipped). Next step / Research question stays a one-line question. The item's session works through the Planned rows in Step order, marks each finished one Done (found by Pipeline ID and Step, never by position) and reports the completed numbers in `steps_done`. Older items may still hold a numbered list in Next step; follow it the same way. On the investigation route a Stage 1 run's steps are the steps of its investigation; on the implementation route they are the implementation plan, ending with the Implementation report. Steps rows sit beside the Stage 1 Drive document, never instead of it.

## Starting sessions

Pass a self-contained prompt to the harness-specific mechanism in [dispatch](dispatch.md):

> Use the horology-supervisor skill in item mode for Pipeline item `<ID>`, run `<RUN-ID>`.

The dispatch adapter owns session creation, monitoring, follow-up and the identifier passed as `session_link` to `finish_run`. If it cannot create the requested session, finish the claimed run as failed with the reason; do not silently run it through another Agent type.
