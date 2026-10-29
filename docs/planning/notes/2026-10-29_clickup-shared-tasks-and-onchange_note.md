# ClickUp shared tasks, first-sync intro and onChange trigger (HOR-12, item 50)

## Context

The founder groups several small Pipeline items under one larger ClickUp task (HOR-12 carries items 49, 50 and 51; HOR-8 carries 43, 44, 45 and 47). ClickUp Sync blocked every item whose task was linked by another item ("ClickUp task also linked to Pipeline …"), so those items never posted. An item's first sync posted nothing, and updates waited for the hourly run. Decided by the founder on 29/10/2026 as direct implementation; no investigation.

## Decision

- **Shared tasks:** several Pipeline items can link one task. Each item keeps its own `_ClickUp Sync` record and posts its own comments, now headed `Pipeline <ID> · <title>` (replacing "Horology updates:"). The task's ClickUp status is changed only when exactly one Pipeline row links it; sharing is counted over every row, so a pilot scope can't hide the other item. The record stores `shared`, and a change to it makes the item pending, so a task that goes back to one item gets that item's status on the next run. `STATUS_MAP` is unchanged.
- **First-sync intro:** an item with no sync record posts one short intro: current Stage and Status and its latest decision (Current decision ID if it is in the register, else the highest Decision ID) with a link to that Decision Register row, or "No decision yet". Items that already have a record, including older records without a snapshot, are not re-introduced.
- **Triggers:** the hourly `applySync` stays the catch-all. A new installable onChange trigger on the Pipeline workbook (`forSpreadsheet(PIPELINE_SHEET_ID).onChange()`, created from the standalone script) runs `syncOnPipelineChange`: it ignores format-only changes, waits 30 s and runs only if no later change arrived, then waits up to 120 s for the script lock. `installTriggers`, `installChangeTrigger`, `removeChangeTrigger` added; `stopSync` removes both.
- **Lock:** one script lock covers manual runs and both triggers; state is saved before the lock is released, so overlapping runs cannot double-post. A change run that can't get the lock logs and leaves the work to the running or next hourly sync.

## Rationale

- Per-item comments keep each item's history readable on a shared task without merging state across items.
- A shared task has no single Pipeline status; leaving its ClickUp status to the founder avoids items overwriting each other's status every run.
- The settle wait turns a burst of edits into one comment; the hourly run covers writes onChange does not see (Sheets API, other Apps Scripts, Decision Register and Document Index workbooks).

## Verification

- `npm test` in `google_appscript/clickup-sync`: 27 offline tests, covering shared-task comments and headings, unchanged status on shared tasks, status restored when unshared, pilot scope, intro content and link, no re-intro for existing records, trigger install/remove, settle supersession, FORMAT skip and lock-busy handling.
- Not verified live: no `clasp push` or trigger install was made, so which writes fire onChange is not confirmed hands-on. The check is in the [Apps Script runbook](../../runbook/subscription-agents/clasp.md#check-which-writes-fire-the-onchange-trigger).

## Follow-ups

- Founder: push, preview, apply, `installTriggers`, then run the onChange check and record which writes fire it.
- Item 49 adds an In progress status to `STATUS_MAP` next.
- The first live run will post intros for items without records (currently 43, 44, 45, 47, 49, 50 and 51).
