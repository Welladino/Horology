# Runs and steps

Both tabs live in the Pipeline workbook next to Master. Map columns by header name.

## Runs tab

One row per run. It records what actually happened.

| Column | Value |
|---|---|
| Run ID | `R-` plus the next unused number; never reuse |
| Pipeline ID | The item's permanent ID |
| Agent type | Claude Code or Codex |
| Run location | Local or Cloud |
| Status | claimed, running, done, failed, released |
| Claimed at | When the claim was made |
| Claim expires | Claimed at + 2 hours |
| Session link | Session ID or URL, when known |
| Skills used | Specialist skills run, in order |
| Plan reason | One line on why those skills |
| Output document IDs | Document Index IDs produced |
| Notes | Blockers, or the old Next step wording when a planner rewrites it |
| Started / Finished | Times |

**Claiming.** Before starting an item, read its latest Runs row. If the status is claimed or running and Claim expires is in the future, someone else has it: skip it. Otherwise add a new row with status claimed and a 2-hour expiry, then read it back. If another live claim for the same item appeared at the same time, keep the earlier one and mark yours released. An expired claim means a run died; the item can be claimed again.

**Closing.** Every run ends with done, failed or released, a finished time and notes on anything left undone.

## Steps tab

Written by the planner when an item needs splitting. The Pipeline row stays the one item; its session works through the steps in order.

| Column | Value |
|---|---|
| Step ID | `S-` plus the next unused number |
| Pipeline ID | The parent item |
| Order | 1, 2, 3… |
| Step / question | One bounded question or task |
| Suggested specialist | A specialist skill name, or blank |
| Status | proposed, done, skipped |
| Output document IDs | Document Index IDs produced |
| Created by run | The run ID that wrote the step |

Mark a step done when its output is saved, or skipped with a note when the founder or the results make it unnecessary.

## Starting sessions

Run from a checkout of the Horology repository, so cloud sessions clone the right repository. Pass a self-contained prompt:

> Use the horology-supervisor skill in item mode for Pipeline item `<ID>`, run `<RUN-ID>`.

| Agent type | Local | Cloud |
|---|---|---|
| Claude Code | `claude -p "<prompt>" --permission-mode auto --output-format json` | `claude --cloud "<prompt>"` |
| Codex | `codex exec "<prompt>"` | `codex cloud exec --env <ENV_ID> "<prompt>"` |

- Start local sessions in the background, a few at a time, and record each session ID from its JSON output.
- `claude --cloud` returns a session link; record it. Cloud sessions use the skills committed under `.claude/skills/` and the connectors on the founder's claude.ai account.
- `codex exec` and `codex cloud exec` need the Codex CLI installed and signed in; `codex cloud exec` is experimental and needs a Codex cloud environment ID. If either isn't available, record the run as failed with the reason.
