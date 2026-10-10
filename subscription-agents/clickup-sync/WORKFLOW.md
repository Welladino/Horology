# Welladino: ClickUp ↔ Pipeline sync

Prepared against the live Master headers on 10 October 2026. The existing live project was imported through clasp; local tests do not confirm
which runtime triggers are currently installed. It uses ClickUp's direct API,
not its official MCP. No custom fields are required. The script transfers records;
it does not run agents, create research, approve spending, or implement code.

## Setup

1. Create a **standalone Apps Script project** at https://script.google.com/ under
   your Welladino Google account. Name it `Welladino — ClickUp Sync`.
   Standalone keeps script access separate from ordinary spreadsheet editors.
2. Create each supplied `.js` file in that project and paste its matching content.
   Delete the empty default Code.js file. Apps Script shares globals across these
   files; no import statements or bundling are needed. Set timezone to Asia/Singapore.
3. Open **Project Settings → Script Properties** and add only **CLICKUP_TOKEN**.
   Edit non-secret settings in **Config.js**, and domain list IDs in **DomainLists.js**.
   Generate a personal ClickUp API token in ClickUp's settings/integrations.
   Enter it directly in Script Properties, never in chat, sheet cells, or source.
   Script project editors can access the token; restrict that access.
4. Run `initializeSheets()` once and authorise Google access. It appends fields
   only; it does not read or write ClickUp. Run it again safely if interrupted.
5. The live Master tables, dropdowns and domain views were updated by Codex.
   For another spreadsheet/test copy, extend its native table to include the new columns:
   Pipeline **A:V** and Decision Register **A:R**, assuming the inspected columns
   have not changed. Use actual last headers if you added other fields meanwhile.
   Preserve all existing dropdown choices. Add Pipeline status `Rework` and
   Decision status `rework` and `parked` if absent. Existing statuses include
   `proposed`, `accepted`, and `rejected`; use those exact lower-case values.
6. Update the domain-view FILTER formulas to include the appended columns,
   preserving their existing domain conditions. Pipeline views currently omit
   Domain, so extend the ending `Master!D2:T` to `Master!D2:V`.
   Decision Register views extend `Master!A2:N` to `Master!A2:R`.
   Extend header rows only where those views already have headers; don't add new
   header rows to headerless views. If a formula differs, retain its structure.
7. Fill Stage for selected pilot rows explicitly; don't infer from old accepted
   decisions. Stage 0 = capture; Stage 1 = investigation; Stage 2 = review;
   Stage 3 = specialist deliverable. Leave other rows until you select them.
8. Configure **PILOT_PIPELINE_IDS** for one or two rows. Create/select the target
   ClickUp domain lists yourself; preserve `open`, `review`, `blocked`, `backlog`,
   `rejected`, `closed`. Use list IDs, not folder/Space IDs.
9. Run `previewSync()`. It performs ClickUp GET requests and prints proposed
   actions/errors in the execution log. It does not change tasks, comments,
   spreadsheet rows, or sync state. Preview requires API access and the schema.
10. Check matches, list selection, statuses, descriptions and decision comments.
    Set `ENABLE_WRITES: true` in Config.js and run `applySync()` manually for the pilot.
11. Inspect the actual tasks and comment links, and run the sync again to check
    it doesn't create duplicates. Test a review round in the pilot before enabling
    ClickUp review ingestion. This live check has not been performed by Codex.
12. Run `installHourlyTrigger()` when satisfied. It installs only one hourly
    trigger; `stopSync()` removes it. Scheduled research agents are configured
    separately. Trigger times aren't exact, and errors are visible in Executions.

## Configuration files

**Script Properties has one entry:** `CLICKUP_TOKEN`.

**Config.js** holds spreadsheet IDs, pilot Pipeline IDs, maximum items per run,
write enablement, ClickUp review enablement, adoption policy and all-row selection.
Use JavaScript booleans `true`/`false`, and an array of IDs, e.g.
`PILOT_PIPELINE_IDS: ['18', '20']`. All three spreadsheet IDs are already filled from
verified records. For test copies, replace those IDs in Config.js.

**DomainLists.js** contains the editable domain-to-list mapping:

```javascript
const DOMAIN_LISTS = {
  'welladino': '',
  'Article Aggregator': '',
  'newsletter': '',
  'ecommerce': ''
};
```

Replace blank values with the corresponding numeric ClickUp list IDs, as strings.
Domain matching is case-insensitive; each domain must have exactly one mapping. Multiple domains can deliberately
point to the same list. A missing mapping stops that item. Domain changes do not
move or duplicate existing tasks automatically.

## Modules

| File | Responsibility |
|---|---|
| Config.js | Non-secret settings, status mapping and token loading |
| DomainLists.js | Domain → ClickUp list mapping |
| Sync.js | Preview/apply entry points, locking and run limits |
| Tasks.js | Task matching, description and per-row coordination |
| Decisions.js | Review checks, approvals and rework transitions |
| DecisionComments.js | One complete comment per decision row |
| ClickUpApi.js | Direct API requests, pacing and list pagination |
| Documents.js | Indexed document lookup and count refresh |
| Sheets.js | Read Master headers/rows and update specific cells |
| SyncState.js | Task IDs, comment IDs, snapshots and pending writes |
| Setup.js | Add schema fields and install/remove the trigger |
| Utils.js | Shared normalization and hashing |

All files belong to **one Apps Script project**, not separate projects. Keep every
module when installing; filenames organize the source but don't isolate globals.
Public functions remain `initializeSheets`, `previewSync`, `applySync`,
`installHourlyTrigger`, and `stopSync`.

## Fields added by initializeSheets

Pipeline: **Stage**, **Review stage**, **Current decision ID**, **ClickUp Pipeline URL**, **Document count**.
ClickUp Pipeline URL is the sole task link; External ID remains optional.

Decision Register: **Pipeline ID**, **Review stage**, **Rework instructions**, **Review source**.
Many Decision Register rows can share a Pipeline ID. Decision IDs must be unique.
Review stage means the deliverable being reviewed: `Stage 1` or `Stage 3`.
While awaiting review, Pipeline Stage is `Stage 2`.

The extra Current decision ID and Review stage remove ambiguity when older
accepted decisions and newer proposals coexist. The script never guesses a match
from a document title or from the existing generic `Welladino — Pipeline` text.
Existing decisions remain unchanged until you explicitly associate them.
No configuration values besides CLICKUP_TOKEN are read from Script Properties.

## Flow and status mapping

| Pipeline | ClickUp |
|---|---|
| Inbox | backlog |
| Parked | blocked |
| Researching | open |
| Awaiting decision | review |
| Approved | open |
| Rework | backlog |
| Handed off | closed |
| Rejected | rejected |

Stage 0 creates or reconciles a mirror task, leaving agent selection unchanged.
Stage 1 agents create/register documents, add a new **proposed** decision with
Pipeline ID/Review stage, and set Pipeline Stage 2, Awaiting decision, Current
decision ID and Review stage. Exactly one proposed decision may be active per item;
resolve or supersede older proposals before selecting a new one.

For **rework in Sheets**, edit the current decision row: Status = `rework` and
write Rework instructions. The next sync sets Pipeline Rework, restores the
originating work stage and sets Agent status Ready, except Manual agents stay
No action. Agents must read the selected Decision Register feedback before working.
Create a new proposed decision for the next review round and retain earlier rows.

For **approval in Sheets**, set current decision Status = `accepted`.
Stage 1 approval sets Pipeline Approved / Stage 3 / Ready. Stage 3 approval sets
Handed off / Stage 3 / No action. Decisions `parked` or `rejected` stop selection.
Sheet decisions are applied once; ordinary subsequent row edits do not repeatedly
queue the same accepted decision.

For **approval in ClickUp**, first set ALLOW_CLICKUP_REVIEW: true in Config.js. Only a transition
from an established `review` baseline is accepted: `open` accepts the selected
proposal, `blocked` parks it, and `rejected` rejects it. `closed` isn't an approval
shortcut. `backlog` isn't interpreted as rework; enter feedback in the register.
One initial sync must publish the current review before ClickUp changes are accepted.

The task API doesn't reliably expose the actor responsible for a status change.
Enable this only for lists whose editors you trust to make these decisions. The
register records ClickUp as the source and explicitly states actor unavailable;
it never treats task creator or assignee as the approving person. If you need
verified reviewer identity, leave this option off and decide in Sheets for now.

## Comments and task descriptions

Each decision row becomes **one complete plain-text comment** containing all its
fields, preserved hyperlink targets, and the register row URL. Updates to that row
update its existing comment. New decision rows create new comments on the same task.
Personal comments are untouched and aren't interpreted as instructions.
Future `REWORK:` comment ingestion is not implemented.

Task descriptions are owned by the mirror, with a stable Pipeline marker,
summary, target/branch, stage, links and review instructions. Put personal notes
in comments. No field in Sheets is overwritten by a ClickUp description/title edit.
ClickUp status changes outside a published review are flagged, not imported.

## Existing tasks, failures and operations

Existing Pipeline task links were migrated from the old mixed reference cells.
For a deliberate existing-task migration, inspect its original description,
preserve any useful context, then opt into ALLOW_ADOPT_EXISTING: true in Config.js temporarily.
Its description will become mirror-owned. Turn the option off after migration.
The script also discovers tasks with the exact Pipeline marker before creating
new ones. Duplicate markers or conflicting task IDs stop the item.

State is kept in Pipeline's **_ClickUp Sync** tab: task IDs, last synced statuses,
review snapshot and decision-comment IDs/hashes. Do not edit this during a run.
Both-side changes, changed proposals during review, domain changes and invalid
links pause the affected item. There are no automatic deletions or task moves.

Before a task/comment POST, a pending marker is persisted. A timeout/error after
submission leaves it pending rather than risking duplicate creation on retry.
Inspect ClickUp and reconcile the task/comment ID in state before clearing pending.
Contact the script maintainer if unsure; don't simply delete the state tab.
Task PUT/comment PUT operations target stable IDs; comments have pending guards too.

Use `stopSync()` and ENABLE_WRITES: false in Config.js to pause. Keep source and a backup of
state before changes. Task/comment creation can't be rolled back by disabling sync.
The script uses a lock and paced requests, caps work per run and rotates its cursor.
No AI is invoked. Console output contains IDs/actions/errors, not tokens or bodies.

## Verification and limitations

Offline mock tests cover preview isolation, creation guards, both review stages,
manual rework, conflicts, duplicate proposals and repeat comment deduplication.
Run `node test-sync.cjs` locally to repeat them. They do not validate live Google
permissions, actual ClickUp list statuses, table settings, or API response behaviour.
Reviewing and editing simultaneously with a sync can still race: Sheets and ClickUp
don't provide one cross-system transaction. Avoid editing pilot records during a run.
On a partial write, inspect the log and records before reconciling; never assume a
failed run made no changes. Scheduled agents need their workflow instructions updated
to populate the added fields and consume Decision Register feedback before rollout.

References: https://developer.clickup.com/docs/rate-limits,
https://developer.clickup.com/reference/createtask,
https://developer.clickup.com/reference/updatetask,
https://developer.clickup.com/reference/createtaskcomment,
https://developer.clickup.com/reference/updatecomment,
https://developers.google.com/apps-script/guides/triggers/installable.

## 10 October column migration and installation update

Pipeline now has 22 columns (A:V). Decision link and ClickUp execution link were
removed. Research / Plan links became Document count. Original fields are preserved
in the Pipeline Migration archive tab, including secondary task links.

Document Index has Pipeline ID in column T. A shared document may list multiple
IDs separated by commas. Counts match exact IDs and deduplicate the same Drive
file. All registered revisions count, regardless of graph inclusion/sync status;
this is a count of indexed documents, not proof of Neon backfill.

Apply sync refreshes selected rows' counts. Preview computes documents without
writing. Run refreshDocumentCounts() to refresh every row without ClickUp access.
Counts are stored values and refresh when these functions run. New agent-created
documents must include Pipeline ID in the Index.

In your existing Apps Script project, add Documents.js; replace Sync.js, Tasks.js,
Sheets.js and Setup.js. Add DOCUMENT_INDEX_SHEET_ID from Config.js to your own
Config.js, preserving your pilot IDs, list mapping and write settings. Do not
replace your configured DomainLists.js. Keep existing-task adoption disabled
until you have reviewed the original description: adoption overwrites it.
