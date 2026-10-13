# ClickUp eligible-row batching and live source update

## Implementation

Added shared Eligibility.js validation, used by both run selection and syncRow. Unmanaged blank-stage rows are skipped before batching; invalid IDs/titles, domains, stages/statuses, review/task conflicts and uncertain task writes are blocked and reported. Manual/No action rows remain eligible. Run-wide duplicate IDs and schema/document-index errors still stop execution.

The batch limit counts eligible attempts only; remote failures still consume slots. Eligible items rotate by permanent positive numeric ID, with lastPipelineId state rather than positional offsets. Skipped/blocked rows receive no document-count writes. Preview never persists cursor/count changes. Existing quota-free ClickUp pacing, review restrictions and pending-write/duplicate guards are retained.

## Verification and publication

32 offline tests passed, including legacy skips, validation failures, review constraints, task conflicts, stable cursor ordering/removal/insertion, large IDs, bounded failures, preview isolation and repeated-write protections. Existing 17 regressions passed alongside 15 new selection/batching checks.

Reauthenticated clasp, cloned the live project into a separate directory, reconciled only the browser-edited Config.js, and rechecked live source immediately before upload. Preserved ENABLE_WRITES true, SYNC_ALL true, empty PILOT_PIPELINE_IDS, MAX_ITEMS_PER_RUN five, ALLOW_CLICKUP_REVIEW false, ALLOW_ADOPT_EXISTING false, and existing domain/list mappings. Only Eligibility.js, Sync.js and Tasks.js differ from the pre-release live source.

clasp push uploaded 15 files to script 1P-mmyz1d65liEF77KaeKabtV855aAlj6Oyk9WKkhfDlT4Eoe3wSFDfGU. A separate fresh clone confirmed all 15 files exactly match maintained local source. Script Properties were not accessed/changed; no sync function, trigger installation/removal, spreadsheet/task creation, Git commit/push or GCP build/deployment was performed. Existing triggers, if installed, will use the updated source. Live agent-to-Sheets-to-ClickUp behavior remains to be tested.

## Live test follow-up

The Luna subagent created and read back Pipeline ID 37 for Article Aggregator (Inbox / Stage 0). ClickUp initially rejected the task because the lists use backlogs while the mapping sent backlog. The operator corrected the mapping in live Config.js; after a native connector search found no matching task, the failed-create pending marker for task:37 was cleared without changing other state. The operator reran applySync and reported success. Current live source was pulled into the comparison directory before committing; Config.js was reconciled into maintained source and all other live source files matched. This records the operator-confirmed live test, not independent verification of task creation or repeat-run deduplication.
