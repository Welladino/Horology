# Apps Script projects

Two Google Apps Script projects support the subscription-agent workflow. Neither runs AI: the Pipeline project serves the web workspace, applies decisions and reconciles Locations with Drive; the optional ClickUp project updates linked planning tasks. Source lives in [`google_appscript/`](../../../google_appscript/), one folder per project, published with clasp ([runbook](https://github.com/Welladino/Horology/blob/main/docs/runbook/subscription-agents/clasp.md)).

| Project                       | Folder                | Attached to           | Does                                                           |
| ----------------------------- | --------------------- | --------------------- | -------------------------------------------------------------- |
| Horology — Pipeline decisions | `pipeline-decisions/` | The Pipeline workbook | Serves the private workspace for decisions, Pipeline items and folders; applies decided rows to Pipeline items |
| Horology — ClickUp Sync       | `clickup-sync/`       | Nothing (standalone)  | One-way status and milestone comments for linked ClickUp tasks |

The decisions project is bound to the Pipeline workbook, so copying the workbook (File → Make a copy) copies it too. ClickUp Sync is standalone: it's optional, and it holds a ClickUp API token that a copy of the workbook must not carry.

The workspace UI source is in `google_appscript/shared-ui/`; its build script generates `pipeline-decisions/src/SharedUi.html`. The page itself is `pipeline-decisions/src/Review.html`.

## Where settings live

The bound decision script discovers its workbook from the open Pipeline. The web page has no open spreadsheet UI, so its project has the Pipeline workbook ID in `WEB_PIPELINE_SHEET_ID`; a copied workbook needs that setting changed before deploying its own page. The Decision Register still comes from the Pipeline's Registers tab.

| Setting                              | Where                                                                                                                          |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| The Pipeline workbook                | The workbook a bound project lives in; for ClickUp Sync, the `PIPELINE_SHEET_ID` Script Property                               |
| Decision workspace web page          | `WEB_PIPELINE_SHEET_ID` and `WEB_APP_URL` in Pipeline decisions `Config.js`; the latter is the Extensions menu link |
| Decision Register and Document Index | Their links on the Pipeline's **Registers** tab, matched by name ("Decision Register", "Document Index"); exactly one row each |
| Domains                              | The Pipeline's **Domains** tab, built from the Root folder rows in Locations                                                   |
| ClickUp task mapping                 | The confirmed URL in each Pipeline row's **ClickUp Pipeline URL** column                                                       |
| ClickUp token                        | ClickUp Sync Script Property `CLICKUP_TOKEN`; never in source, sheets or chat                                                  |
| Behaviour switches                   | Each project's `Config.js` (write gates, intervals and batch size)                                                            |

Triggers and authorisation never come with a copy; the new owner installs them once.

## Pipeline decisions

When the current decision for an item that is **Awaiting decision** is set to accepted, rework, parked or rejected in the Decision Register, the item moves on:

| Decision                           | Review stage | Pipeline becomes                  |
| ---------------------------------- | ------------ | --------------------------------- |
| accepted                           | Investigation proposal | Approved, Stage 3, Ready          |
| accepted                           | Specialist deliverable | Completed, Stage 4, No action     |
| rework (needs Rework instructions) | either | Rework, back to the reviewed stage, Ready |
| parked                             | Investigation / Specialist | Parked, Stage 2 / Stage 4, No action |
| rejected                           | Investigation / Specialist | Rejected, Stage 2 / Stage 4, No action |

Only Claude Code and Codex rows are made Ready; Manual and Unassigned get No action. It also sets the item's Updated date and, if blank, the decision's Decision Date. The supervisor creates the Stage 4 synthesis immediately after Stage 3 and before this final review. The decision script preserves Stage 4 when the founder decides on the specialist deliverable. The rules come from [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml); a unit test checks they agree.

* It acts only on items still Awaiting decision, using the decision named in Current decision ID, so a decision is never applied twice and old accepted decisions are never replayed. It keeps no state of its own.
* Proposed decisions are skipped. Problems (no Current decision ID, a decision for another item or stage, rework without instructions) are reported and that item is left unchanged.
* To change your mind after a decision was applied, **revise** it on the decision page (below); editing the decision's Status again in the sheet does nothing.
* The web workspace applies a saved decision immediately. A remaining edit trigger can process a person's direct Decision Register edit. Apps Script and API writes do not fire edit triggers; their writers must call `applyDecisions` explicitly. The former ten-minute timer was removed by the founder.

Each cell write finds its row again by permanent ID (ID or Decision ID) immediately before writing, so a sort, insert or agent write in between can't redirect it to another item; a missing or duplicated ID stops the write.

Functions: `previewDecisions` (reports, writes nothing), `applyDecisions` (a preview while `ENABLE_WRITES` is false), `installTriggers`, `stopTriggers`. They remain available to administrators in the Apps Script editor, while **Open Horology workspace** is the only entry under **Extensions → Horology — Pipeline decisions**.

### Founder review web page

The private Horology workspace is an Apps Script HTML web app in the same project. Its deployment executes as the owner and is restricted to the owner's account. The Extensions menu opens that workspace's private deployment URL. Public documentation must not embed it. The app creates no Sheets tab; it reads the Decision Register's **Options** tab and the Pipeline's **Steps** tab when they exist, and needs no Cloud Run change.

The Decisions view shows expandable rows only; opening a decision shows its options and input form. It lists proposed decisions only when they are the current decision of a Pipeline item still Awaiting decision, and displays decided records read-only. It shows the question, the one-line proposal, the options as cards (summary, key figures as bullets, the recommended one marked), the reason as bullets, the item's planned steps and evidence links. Options come from the decision's rows on the Options tab; a decision without rows falls back to the option codes in its text (`Option B`, `Proposed (Option B):`, `Alternatives: A …; C …`), which are hints the founder checks. Planned steps come from the item's Steps rows, or else the numbered lines of its Next step. The founder may edit the final decision wording. Choosing an alternative requires a short founder reason, not a rework cycle.

The **Pipeline** view reads every row with an ID from Pipeline Master. It offers cards, rows, search, and client-side filters for Domain, Status, Entity, Type, Agent status, Agent type, Run location and Stage. The Entity choices narrow with Domain; blank values can be filtered. Review stage is left to the Decisions view. Opening an item shows its scope, next step, revisit trigger, status and links. **Edit item** saves Title, Type, Summary / Why, Next step / Research question, Revisit trigger, Agent status, Agent type and Run location by permanent ID after checking that the row has not changed since it was opened. Domain, Entity, Status and Stage are visible but not directly editable. A valid Inbox selection of Ready moves Stage 0 to Stage 1; other Agent status changes follow the workflow rules. The page refreshes the view after a decision or item is saved or an item is added.

The Decisions view groups all recorded decisions by Pipeline ID. A Pipeline item awaiting review appears once in **Needs your review**, with its earlier decisions inside the same expandable entry. Other items appear in **Decision history**. Each decision opens its own review or read-only detail page.

On save, the server re-reads both Master sheets by permanent IDs, checks that the proposal has not changed, writes the decision wording/reason or rework instructions, records the review source and date, and writes Status last. It immediately applies that one decision to the Pipeline using the existing rules. If the Pipeline update fails, the page says the decision is saved and an administrator must run `applyDecisions`. The page never creates a new decision row.

**Revise** appears on a decided record that is still its item's Current decision ID while the item is Approved, Rework, Parked, Rejected or Completed (never Inbox, Researching or Awaiting decision). The founder picks the new outcome (park, reject, rework with instructions, or accept an option with its wording) and a reason. Under the script lock the server re-reads both Master sheets by ID, checks nothing changed since the page opened, writes Status, appends "Founder revised *old* to *new* on *date*: *reason*" to Reason and the revision to Review source, then sets the item's Status, Stage and Agent status as that outcome would from review (`revise` in `workflow.yaml`, `revise()` in `Rules.js`) and its Updated date. Ready is set only for Claude Code and Codex rows. A new review round still creates a new decision row through an agent.

The **Add Pipeline item** view writes a new Master row. It reads Domain and Entity choices from the Pipeline's Domains tab and dropdown choices from Master, uses the same validation as the former workbook dialog, and allocates the next permanent ID under a script lock. A normal capture starts in Inbox/Stage 0; choosing Ready starts at Stage 1 and requires an agent and a Next step.

## Locations

The workspace **Folders** view presents Locations as a searchable path browser: roots, the current folder level, and selected-folder details. Breadcrumbs navigate deeper paths; colored chips distinguish folder roles. Rows whose parent cannot be found appear under **Parent not found**. Browsing is read-only.

**Check Drive & update Locations** is an explicit button in that view. It opens each listed folder by its Location link, updates only **Name** and **Parent** cells to match Drive, then reports updates, inaccessible or moved folders, and unlisted subfolders. It never creates, moves or renames anything in Drive. The web app uses the advanced Drive service v3 with read-only Drive access, including shared drives.

## ClickUp Sync

This optional standalone Apps Script updates ClickUp tasks already linked in Pipeline Master. ClickUp is a planning notebook; Sheets and the registers remain the operational record. The founder may use AI to suggest an existing task, then confirms its URL in **ClickUp Pipeline URL**. The sync never creates tasks, edits their names or descriptions, or imports ClickUp changes into Sheets. A task can be linked to only one Pipeline item.

### Status and comments

Pipeline status maps one way to ClickUp: Inbox and Rework → backlogs; Parked → blocked; Researching and Approved → open; Awaiting decision → review; Rejected → rejected. **Completed does not change ClickUp status**; the founder closes the task manually. The ClickUp list must support the mapped statuses. A later mapped Pipeline change can replace a status set manually in ClickUp.

The run compares Pipeline status and stage, Decision Register records, and Document Index links with the last successful snapshot. It posts one combined "Horology updates:" comment per linked task when milestones or indexed documents change, with a Horology workspace link and the Pipeline sheet row. Completed can still produce this comment. The first run establishes a baseline and aligns mapped statuses without reposting historical decisions and documents. Unindexed Drive files are not detected; task descriptions and personal comments are left alone.

### Selection and recovery

Unlinked rows are skipped. Invalid URLs, duplicate task mappings, conflicting old task IDs and uncertain writes block the item. Duplicate Pipeline or Decision IDs, missing headers and invalid Document Index data stop the run. Every write finds its row again by ID immediately before writing, never by the position read earlier; a row whose ID has disappeared or is duplicated is not written. Only changed or new baselines call ClickUp. Each run handles up to `MAX_ITEMS_PER_RUN` (50) pending items with an ID cursor; preview writes nothing and includes the exact proposed comment in its output.

The Pipeline's **`_ClickUp Sync`** tab holds task IDs, snapshots, pending comment markers and the cursor. A timeout after a comment request leaves a pending marker to prevent a duplicate; inspect ClickUp and reconcile the state before retrying. The script locks runs and paces API calls; preview output includes the proposed comment, so avoid sharing its logs externally. `CLICKUP_TOKEN` and `PIPELINE_SHEET_ID` are its only required Script Properties; old `LIST_<Domain>` properties are ignored.

Public functions: `previewSync`, `applySync`, `installHourlyTrigger`, `stopSync`, `testClickUpConnection`, `initializeSheets`, and `refreshDocumentCounts`. The last refreshes Document count separately; ClickUp sync itself does not write that field.

| Module | Responsibility |
| --- | --- |
| Config.js | Write gate, batch size, status mapping and token |
| Registers.js | Pipeline and register locations |
| Sync.js | Preview/apply, lock and pending batch |
| Eligibility.js | Link validation and batch ordering |
| Tasks.js | Status and comment writes |
| Notebook.js | Milestone snapshots and comment text |
| ClickUpApi.js | Direct API requests and pacing |
| Documents.js | Indexed documents and separate count refresh |
| Sheets.js | Master reads and count writes |
| SyncState.js | Persistent `_ClickUp Sync` state |
| Setup.js | Schema and hourly trigger |
| Utils.js | Normalisation and hashing |

## Tests

Each folder has offline tests (`npm test`) with fake sheets, Drive and ClickUp; nothing calls Google or ClickUp. They cover decision and revise rules, Options and Steps tabs with their text fallbacks, folder checks, and the ClickUp updater's linked-task guard, one-way status mapping, comment deduplication, preview isolation and bounded batch. They do not prove live permissions, list statuses or API behaviour: after publishing, run the preview in the live project.
