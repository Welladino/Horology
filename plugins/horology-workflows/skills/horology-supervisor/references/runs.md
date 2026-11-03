# Runs

Runs are recorded in the execution history (Neon), through the document-graph connector. You make two calls per run: `claim_item` at the start and `finish_run` at the end. Specialists also call `reserve_id` for each new Decision or Document ID and `check_register_write` before each register write, passing the run ID. Everything else (status changes, outputs, decisions) is recorded from the sheets by the sync job, so don't report it.

## Claiming

Call `claim_item(pipeline_id, agent_type, run_location, kind)` once per item, before any work on it:

- `agent_type`: the platform you run on, Claude Code or Codex.
- `run_location`: the item's Run location, Local or Cloud (blank in the sheet means Local).
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

The planner, or an implementation-route run at Stage 1, writes an item's steps on the Pipeline's **Steps** tab, one row per step: Pipeline ID, Step, Task, Specialist (optional) and Status (Planned, Done or Skipped). Next step / Research question stays a one-line question. The item's session works through the Planned rows in Step order, marks each finished one Done (found by Pipeline ID and Step, never by position) and reports the completed numbers in `steps_done`. Older items may still hold a numbered list in Next step; follow it the same way.

## Starting sessions

Run from a checkout of the Horology repository, so cloud sessions clone the right repository. Pass a self-contained prompt:

> Use the horology-supervisor skill in item mode for Pipeline item `<ID>`, run `<RUN-ID>`.

| Agent type | Local | Cloud |
|---|---|---|
| Claude Code | `claude -p "<prompt>" --permission-mode auto --output-format json` | `claude --cloud "<prompt>"` |
| Codex desktop | Native `create_thread`, current Horology project, local environment | Native `create_thread`, configured Codex cloud environment |

- On Codex desktop, the founder's dispatch request authorises creating the item threads and sending their coordination follow-up. Call `list_projects` first and use the current Horology project for Local rows. For Cloud rows, call `list_cloud_environments` and use the already configured compatible environment; do not invent one.
- Call `create_thread` once per claimed item with the self-contained prompt and a short title containing the Pipeline ID. Do not request a worktree unless the founder explicitly asked for one. Record the returned `threadId` and `hostId`; a `clientThreadId` means setup is still pending and is not valid for thread tools yet.
- After a real `threadId` is returned, call `send_message_to_thread` once with a coordination follow-up containing that thread ID and instructing the item session to pass it as `session_link` to `finish_run`. Do not send repeated progress prompts.
- Coordinate up to eight native threads at a time with `wait_threads`. Keep each returned cursor as `afterCursor`, continue until every thread completes or needs attention, and use `timeoutMs: 0` only for an immediate snapshot. Commentary does not wake the wait. Leave approvals and user-input requests in their item thread for the founder; do not answer them on the founder's behalf.
- A completed native thread gives the dispatcher its final result. For a thread that needs attention, report the thread ID and the requested action. Do not repeatedly call `read_thread`; use it only when the compact wait result does not identify the action needed.
- The Codex CLI is an explicit fallback, not the default. Use `codex exec "<prompt>"` for Local or `codex cloud exec --env <ENV_ID> "<prompt>"` for Cloud only when the native `create_thread` capability is absent or returns an unavailability/capability error before creating a thread. Do not fall back because a created thread fails, needs attention, or has an ambiguous project/environment; report that state instead. The CLI must be installed and signed in, and cloud fallback needs an existing environment ID. If neither native creation nor the applicable CLI path is available, finish the claim as failed with the reason.
- Start Claude local sessions in the background, a few at a time, and note each session ID from its JSON output.
- `claude --cloud` returns a session link. Cloud sessions use the skills and connectors on the founder's claude.ai account, whatever repository they clone.
