# Runs

Runs are recorded in the execution history (Neon), through the document-graph connector. You make two calls per run: `claim_item` at the start and `finish_run` at the end. Everything else (status changes, outputs, decisions) is recorded from the sheets by the sync job, so don't report it.

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
| steps_done | Which numbered steps from Next step were completed, e.g. "1, 2" |
| notes | A few lines on the result or the blocker; the planner puts the old Next step wording here |
| session_link | The session URL or ID, when known |

## Steps

The planner writes an item's steps as a numbered list in Next step / Research question, one bounded question or task per line, optionally ending with the suggested specialist in brackets. The item's session works through them in order and reports the completed numbers in `steps_done`.

## Starting sessions

Run from a checkout of the Horology repository, so cloud sessions clone the right repository. Pass a self-contained prompt:

> Use the horology-supervisor skill in item mode for Pipeline item `<ID>`, run `<RUN-ID>`.

| Agent type | Local | Cloud |
|---|---|---|
| Claude Code | `claude -p "<prompt>" --permission-mode auto --output-format json` | `claude --cloud "<prompt>"` |
| Codex | `codex exec "<prompt>"` | `codex cloud exec --env <ENV_ID> "<prompt>"` |

- Start local sessions in the background, a few at a time, and note each session ID from its JSON output.
- `claude --cloud` returns a session link. Cloud sessions use the skills committed under `.claude/skills/` and the connectors on the founder's claude.ai account.
- `codex exec` and `codex cloud exec` need the Codex CLI installed and signed in; `codex cloud exec` is experimental and needs a Codex cloud environment ID. If either isn't available, finish the run as failed with the reason.
