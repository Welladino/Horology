# Pipeline decisions

Applies the founder's decisions to the Pipeline. When the current decision for an item that is **Awaiting decision** is set to accepted, rework, parked or rejected in the Decision Register, this script moves the item on:

| Decision | Review stage | Pipeline becomes |
|---|---|---|
| accepted | Stage 1 | Approved, Stage 3, Ready |
| accepted | Stage 3 | Handed off, Stage 3, No action |
| rework (needs Rework instructions) | Stage 1 or 3 | Rework, back to that stage, Ready |
| parked | either | Parked, Stage 2, No action |
| rejected | either | Rejected, Stage 2, No action |

Only Claude Code and Codex rows are made Ready; Manual and Unassigned rows get No action. It also sets the item's Updated date and, if blank, the decision's Decision Date. The rules come from [`workflow.yaml`](../../plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml); a test checks they agree.

No AI, no ClickUp, no secrets. It reads Pipeline Master and Decision Register Master and writes only those cells.

## Safe to run any time

- It only acts on items whose Status is still Awaiting decision, using the decision named in their Current decision ID. Once applied the item leaves Awaiting decision, so a decision is never applied twice and old accepted decisions are never replayed. It keeps no state of its own.
- Proposed decisions are skipped. Problems (no Current decision ID, a decision for another item or stage, rework without instructions) are logged and that item is left unchanged.
- To change your mind after a decision was applied, edit the Pipeline row yourself; editing the decision again does nothing.

## Functions

| Function | Does |
|---|---|
| `previewDecisions()` | Logs what would change; writes nothing |
| `applyDecisions()` | Applies them (a preview while `ENABLE_WRITES` is false) |
| `installTriggers()` | Runs `applyDecisions` every `CHECK_EVERY_MINUTES` and straight after a person edits the Decision Register |
| `stopTriggers()` | Removes both triggers |

The edit trigger only fires for people's edits; decisions written by an AI session through the Sheets API are picked up by the timer.

## Live project

[Horology — Pipeline decisions](https://script.google.com/d/1QyqlFEA6pstwD7XY8hvfs3jf3LNBWCujw59B0Ki33N60Q1cNMbzvYi4u/edit), script ID `1QyqlFEA6pstwD7XY8hvfs3jf3LNBWCujw59B0Ki33N60Q1cNMbzvYi4u`, created 16 October 2026 under the founder's Welladino account.

## Layout and development

- `src/`: the Apps Script project (`Config.js` holds the two spreadsheet IDs and settings).
- `tests/`: offline tests, no Google access.

```sh
npm test
```

It's a standalone project, separate from [clickup-sync](../clickup-sync/README.md), so it works without ClickUp and can later be shared on its own: another user needs only their two spreadsheet IDs in `Config.js`. Setup and publishing: [clasp runbook](../../docs/runbook/subscription-agents/clasp.md#pipeline-decisions-project).
