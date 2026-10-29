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
| accepted (answered)                | Implementation question | In progress, Stage 3, Ready (implementation resumes) |
| rework (needs Rework instructions) | any | Rework, back to the reviewed stage (Stage 1 for an Investigation proposal, else Stage 3), Ready |
| parked                             | Investigation / Specialist / Implementation question | Parked, Stage 2 / Stage 4 / Stage 3, No action |
| rejected                           | Investigation / Specialist / Implementation question | Rejected, Stage 2 / Stage 4 / Stage 3, No action |

Only Claude Code and Codex rows are made Ready; Manual and Unassigned get No action. It also sets the item's Updated date and, if blank, the decision's Decision Date. The supervisor creates the Stage 4 synthesis immediately after Stage 3 and before this final review. The decision script preserves Stage 4 when the founder decides on the specialist deliverable. The rules come from [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml); a unit test checks they agree.

* It acts only on items still Awaiting decision, using the decision named in Current decision ID, so a decision is never applied twice and old accepted decisions are never replayed. It keeps no state of its own.
* Proposed decisions are skipped. Problems (no Current decision ID, a decision for another item or stage, rework without instructions) are reported and that item is left unchanged.
* To change your mind after a decision was applied, **revise** it on the decision page (below); editing the decision's Status again in the sheet does nothing.
* The web workspace applies a saved decision immediately. A remaining edit trigger can process a person's direct Decision Register edit. Apps Script and API writes do not fire edit triggers; their writers must call `applyDecisions` explicitly. The former ten-minute timer was removed by the founder.

Each cell write finds its row again by permanent ID (ID or Decision ID) immediately before writing, so a sort, insert or agent write in between can't redirect it to another item; a missing or duplicated ID stops the write.

Functions: `previewDecisions` (reports, writes nothing), `applyDecisions` (a preview while `ENABLE_WRITES` is false), `installTriggers`, `stopTriggers`. They remain available to administrators in the Apps Script editor, while **Open Horology workspace** is the only entry under **Extensions → Horology — Pipeline decisions**.

### Founder review web page

The private Horology workspace is an Apps Script HTML web app in the same project. Its deployment executes as the owner and is restricted to the owner's account. The Extensions menu opens that workspace's private deployment URL. Public documentation must not embed it. The app creates no Sheets tab; it reads the Decision Register's **Options** tab and the Pipeline's **Steps** tab when they exist, and needs no Cloud Run change.

**Loading.** Lists carry only what a list shows; details are read when something is opened. `getReviewDashboard` returns one summary per decision (ID, Pipeline ID, title, domain, stage, status, question cut to about 220 characters, whether it needs review, and a date for its age: the Decision Date, or for a proposal its item's Updated date) and reads only the two Master sheets. `getDecisionReview(id)` returns one decision in full (proposal, reason, options, steps, links, the version a save is checked against), read fresh. `getPipelineOverview` returns `{rows}` with the list, filter and sort fields and a one-line summary; `getPipelineItem(id)` returns one item in full with its Steps rows and edit version, read fresh; `searchPipelineItems(query)` returns the IDs whose list fields or long text (Summary / Why, Next step, Revisit trigger) contain every word of the query. Each request opens each workbook once (`openBook` in `Registers.js`).

**Caching.** The two lists are kept in the script cache (`CacheService`, `LIST_CACHE` in `WebApp.js`) for 60 seconds, split into chunks of at most 30,000 characters so each value stays under the 100 KB per-key limit. Every write from the page clears them, and **Refresh** reads the sheets again; an edit made in the sheets or by an agent shows in a list within a minute, and at once in any decision or item opened, because details are never cached. The deployment runs as the owner and only the owner can open it, so the shared script cache holds nothing another person could read.

**First paint.** `doGet` embeds the first Decisions list in the page (as JSON in a `<script type="application/json">` element, with `<` escaped), so the Decisions view paints without a second round trip; if that read fails, the page loads the list itself and shows the error with **Try again**. The Pipeline list then loads in the background, so the Pipeline tab usually opens without waiting.

**Navigation.** The view is kept in the URL hash (`#decisions`, `#decision/9`, `#pipeline`, `#item/51`, `#folders`, `#add`) through `google.script.history`, so the browser's Back button works and a decision or item can be bookmarked. A decision page links to its Pipeline item, and an item with a Current decision ID links to that decision. A failed load shows the error and **Try again** instead of a blank page. `/` jumps to the top bar's search.

**Look.** The page follows the Triage board design the founder chose from mockups (item 52): IBM Plex Sans from Google Fonts, a light ground (`#eef1f3`) with ink `#1e2a32`, white panels with a 1px `#d5dde2` border and 8–10px corners, and one accent (`#0f5f73`). A dark top bar holds the navigation (Decisions with the number needing review, Pipeline, Folders), one search box that searches the view on screen (from an item or Add item it opens the board), the amber **Add item** button and a link to the Pipeline sheet. Colour tokens and the shared buttons, inputs and pills are in `google_appscript/shared-ui/`. Text meets 4.5:1 contrast, controls are at least 44px high, and at phone width the top bar wraps, the inbox stacks above the reading pane and the board scrolls sideways.

The **Decisions** view is an inbox beside a reading pane. The inbox (about 340–400px) has **Needs review** and **History** lists; each row shows the Decision ID, domain, age, title and a one-line question, and the open decision is highlighted with an accent bar. Opening one reads it fresh (`getDecisionReview`) into the reading pane and sets `#decision/<ID>`. The pane's header line gives Decision ID, domain, Pipeline ID, status and review stage, then the item title as the heading, then Question, the proposal (or recorded decision), Options as cards (summary, key figures as bullets, the recommended one bordered in the accent and labelled RECOMMENDED), Why (the reason as bullets), the item's planned steps and revisit trigger. A **Your decision** panel beside them holds the outcome form, or for a decided current decision the revise form, and links to the Pipeline item and evidence. Proposed decisions are listed only when they are the current decision of a Pipeline item still Awaiting decision; decided records are read-only. For a proposal the option cards are the choice an approval records; other outcomes leave them visible but disabled. Options come from the decision's rows on the Options tab; a decision without rows falls back to the option codes in its text (`Option B`, `Proposed (Option B):`, `Alternatives: A …; C …`), which are hints the founder checks. Planned steps come from the item's Steps rows, or else the numbered lines of its Next step. The founder may edit the final decision wording. Choosing an alternative requires a short founder reason, not a rework cycle. For an **Implementation question** (implementation route) the accept outcome reads **Answer and resume Stage 3**: the item returns to In progress, Stage 3 and Ready for its platform.

The **Pipeline** view is a board of every row with an ID from Pipeline Master, in five columns: **Inbox** (Inbox or blank Status); **Investigating or planning** (Researching, In progress, Approved or Rework before Stage 3); **Waiting for you** (Awaiting decision); **Building or delivering** (those statuses at Stage 3); **Done** (Completed, most recently updated first, 10 shown, then **Show more**). Other columns show 20 cards at a time. Parked and Rejected items are off the board and listed from **Show**, which also offers every item as cards. Each card shows `#ID · domain`, a Type tag (Build types — Feature, Enhancement, Refactor, Fix — and Investigate types in different colours), the title, and the stage and status, or for an item waiting on the founder its current decision and review stage. The Domain and Type filters sit above the board (Type also offers **Build** and **Investigate**), with Sort (sheet order, needs attention first, newest, recently updated) and **More filters** for Status, Entity, Agent status, Agent type, Run location and Stage. The Entity choices narrow with Domain; blank values can be filtered. Review stage is left to the Decisions view. Search matches every word of the query: the list's own fields at once, and the long text through `searchPipelineItems` a moment later. The Decisions history shows 50 items at a time. Opening an item shows its scope, next step, revisit trigger, status and links. **Edit item** saves Title, Type, Summary / Why, Next step / Research question, Revisit trigger, Agent status, Agent type and Run location by permanent ID after checking that the row has not changed since it was opened. Domain, Entity, Status and Stage are visible but not directly editable. A valid Inbox selection of Ready moves Stage 0 to Stage 1; other Agent status changes follow the workflow rules. Ready can be chosen from Inbox, Rework or Approved, and for an implementation-route Type (Feature, Enhancement, Refactor, Fix; `IMPLEMENTATION_TYPES` in `ItemRules.js`) also from In progress, so a failed or stopped implementation run can be selected again at its Stage. The Type list adds Fix; the live dropdown wins when the Master column has one. After a decision or item is saved or an item is added, the page reloads the lists, and a saved item is shown as read back from the sheet.

On save, the server re-reads both Master sheets by permanent IDs, checks that the proposal has not changed, writes the decision wording/reason or rework instructions, records the review source and date, and writes Status last. It immediately applies that one decision to the Pipeline using the existing rules. If the Pipeline update fails, the page says the decision is saved and an administrator must run `applyDecisions`. The page never creates a new decision row.

**Revise** appears on a decided record that is still its item's Current decision ID while the item is Approved, Rework, Parked, Rejected or Completed (never Inbox, Researching, In progress or Awaiting decision). The founder picks the new outcome (park, reject, rework with instructions, or accept an option with its wording) and a reason. Under the script lock the server re-reads both Master sheets by ID, checks nothing changed since the page opened, writes Status, appends "Founder revised *old* to *new* on *date*: *reason*" to Reason and the revision to Review source, then sets the item's Status, Stage and Agent status as that outcome would from review (`revise` in `workflow.yaml`, `revise()` in `Rules.js`) and its Updated date. Ready is set only for Claude Code and Codex rows. A new review round still creates a new decision row through an agent.

The **Add Pipeline item** view writes a new Master row. It reads Domain and Entity choices from the Pipeline's Domains tab and dropdown choices from Master, uses the same validation as the former workbook dialog, and allocates the next permanent ID under a script lock. A normal capture starts in Inbox/Stage 0; choosing Ready starts at Stage 1 and requires an agent and a Next step.

## Locations

The workspace **Folders** view presents Locations as a searchable path browser: roots, the current folder level, and selected-folder details. Breadcrumbs navigate deeper paths; colored chips distinguish folder roles. Rows whose parent cannot be found appear under **Parent not found**. Browsing is read-only.

**Check Drive & update Locations** is an explicit button in that view. It opens each listed folder by its Location link, updates only **Name** and **Parent** cells to match Drive, then reports updates, inaccessible or moved folders, and unlisted subfolders. It never creates, moves or renames anything in Drive. The web app uses the advanced Drive service v3 with read-only Drive access, including shared drives.

## ClickUp Sync

This optional standalone Apps Script updates ClickUp tasks already linked in Pipeline Master. ClickUp is a planning notebook; Sheets and the registers remain the operational record. The founder may use AI to suggest an existing task, then confirms its URL in **ClickUp Pipeline URL**. The sync never creates tasks, edits their names or descriptions, or imports ClickUp changes into Sheets. Several Pipeline items can link the same task, when each is a smaller part of a larger ClickUp goal; each item keeps its own sync state and posts its own comments.

### Status and comments

Pipeline status maps one way to ClickUp: Inbox and Rework → backlogs; Parked → blocked; Researching, Approved and In progress → open; Awaiting decision → review; Rejected → rejected. The linked lists' statuses are open, closed, review, blocked, rejected and backlogs; a list without a mapped status rejects the change, so keep `STATUS_MAP` to those names. **Completed does not change ClickUp status**; the founder closes the task manually. The ClickUp list must support the mapped statuses. A later mapped Pipeline change can replace a status set manually in ClickUp. A task linked by more than one Pipeline item has no single Pipeline status, so the sync leaves its ClickUp status alone and only comments; when it is linked by one item again, that item's status is applied on the next run.

The run compares Pipeline status and stage, Decision Register records, and Document Index links with the last successful snapshot. Each item posts one combined comment when its milestones or indexed documents change, headed `Pipeline <ID> · <title>` so items sharing a task stay distinguishable, with a Horology workspace link and the Pipeline sheet row. Completed can still produce this comment. An item's first sync posts one short intro instead: its current Stage and Status and its latest decision (the Current decision ID when it is in the register, otherwise the highest Decision ID) with a link to that Decision Register row, or "No decision yet". Historical decisions and documents are not reposted. Items that already have a `_ClickUp Sync` record are never re-introduced. Unindexed Drive files are not detected; task descriptions and personal comments are left alone.

### Selection and recovery

Unlinked rows are skipped. Invalid URLs, conflicting old task IDs and uncertain writes block the item. Duplicate Pipeline or Decision IDs, missing headers and invalid Document Index data stop the run. Every write finds its row again by ID immediately before writing, never by the position read earlier; a row whose ID has disappeared or is duplicated is not written. Only changed items, new items and items whose task became shared or unshared call ClickUp. Each run handles up to `MAX_ITEMS_PER_RUN` (50) pending items with an ID cursor; preview writes nothing and includes the exact proposed comment in its output.

The Pipeline's **`_ClickUp Sync`** tab holds task IDs, snapshots, pending comment markers and the cursor. A timeout after a comment request leaves a pending marker to prevent a duplicate; inspect ClickUp and reconcile the state before retrying. One script lock covers manual runs and both triggers, so overlapping runs wait or stop instead of double-posting; the script also paces API calls; preview output includes the proposed comment, so avoid sharing its logs externally. `CLICKUP_TOKEN` and `PIPELINE_SHEET_ID` are its only required Script Properties; old `LIST_<Domain>` properties are ignored.

### Triggers

`applySync` runs hourly as the catch-all. An installable **onChange** trigger on the Pipeline workbook, created from the standalone script with `forSpreadsheet(PIPELINE_SHEET_ID)`, runs `syncOnPipelineChange` so updates post soon after a change. It ignores formatting-only changes, waits `CHANGE_SETTLE_SECONDS` (30) and runs only if no later change arrived, so a burst of edits gives one comment, then waits up to `CHANGE_LOCK_WAIT_SECONDS` (120) for a running sync before leaving the change to the next run. People's edits in the Sheets editor fire it. Writes through the Sheets API (agents, connectors) and from other Apps Scripts (the web workspace) are not expected to fire it, and Decision Register and Document Index changes are in other workbooks; the hourly run picks all of those up. Each change run sleeps for the settle time, which counts toward the account's daily trigger runtime.

Public functions: `previewSync`, `applySync`, `installHourlyTrigger`, `installChangeTrigger`, `removeChangeTrigger`, `installTriggers` (both), `stopSync` (removes both), `testClickUpConnection`, `initializeSheets`, and `refreshDocumentCounts`. The last refreshes Document count separately; ClickUp sync itself does not write that field.

| Module | Responsibility |
| --- | --- |
| Config.js | Write gate, batch size, status mapping and token |
| Registers.js | Pipeline and register locations |
| Sync.js | Preview/apply, onChange handler, lock and pending batch |
| Eligibility.js | Link validation and batch ordering |
| Tasks.js | Status and comment writes |
| Notebook.js | Milestone snapshots, first-sync intro and comment text |
| ClickUpApi.js | Direct API requests and pacing |
| Documents.js | Indexed documents and separate count refresh |
| Sheets.js | Master reads and count writes |
| SyncState.js | Persistent `_ClickUp Sync` state |
| Setup.js | Schema, hourly and Pipeline onChange triggers |
| Utils.js | Normalisation and hashing |

## Tests

Each folder has offline tests (`npm test`) with fake sheets, Drive and ClickUp; nothing calls Google or ClickUp. They cover decision and revise rules, Options and Steps tabs with their text fallbacks, the light lists and fresh details, list caching (chunk size, invalidation by every web write, Refresh), the embedded first list, the page's routing, inbox lists and age, board columns, Type groups, search and sort, folder checks, and the ClickUp updater's linked-task guard, shared tasks, first-sync intro, one-way status mapping, comment deduplication, preview isolation, bounded batch, trigger install and removal, and the onChange settle and lock behaviour. They do not prove live permissions, list statuses or API behaviour: after publishing, run the preview in the live project.
