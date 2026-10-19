# Apps Script projects

Three Google Apps Script projects support the subscription-agent workflow. None of them runs AI: they move records between the registers and ClickUp, apply the founder's decisions, and keep the Locations tab in step with Drive. Source lives in [`google_appscript/`](https://github.com/Welladino/Horology/tree/main/google_appscript), one folder per project, published with clasp ([runbook](https://github.com/Welladino/Horology/blob/main/docs/runbook/subscription-agents/clasp.md)).

| Project | Folder | Attached to | Does |
|---|---|---|---|
| Horology — Pipeline decisions | `pipeline-decisions/` | The Pipeline workbook | Applies decided Decision Register rows to their Pipeline items |
| Horology — Workbook | `pipeline-locations/` | The Pipeline workbook | Folder tree view, and Name and Parent kept in step with Drive |
| Horology — ClickUp Sync | `clickup-sync/` | Nothing (standalone) | Optional mirror of Pipeline items and decisions to ClickUp |

The two core projects are bound to the Pipeline workbook, so copying the workbook (File → Make a copy) copies them too. ClickUp Sync is standalone: it's optional, and it holds a ClickUp API token that a copy of the workbook must not carry.

## Where settings live

No project has a workspace's sheet IDs or domain names in its code.

| Setting | Where |
|---|---|
| The Pipeline workbook | The workbook a bound project lives in; for ClickUp Sync, the `PIPELINE_SHEET_ID` Script Property |
| Decision Register and Document Index | Their links on the Pipeline's **Registers** tab, matched by name ("Decision Register", "Document Index"); exactly one row each |
| Domains | The Pipeline's **Domains** tab, built from the Root folder rows in Locations |
| ClickUp lists | ClickUp Sync Script Properties, one `LIST_<Domain>` per mirrored domain |
| ClickUp token | ClickUp Sync Script Property `CLICKUP_TOKEN`; never in source, sheets or chat |
| Behaviour switches | Each project's `Config.js` (write gates, intervals, batch size, review and adoption options) |

Triggers and authorisation never come with a copy; the new owner installs them once.

## Pipeline decisions

When the current decision for an item that is **Awaiting decision** is set to accepted, rework, parked or rejected in the Decision Register, the item moves on:

| Decision | Review stage | Pipeline becomes |
|---|---|---|
| accepted | Stage 1 | Approved, Stage 3, Ready |
| accepted | Stage 3 | Handed off, Stage 3, No action |
| rework (needs Rework instructions) | Stage 1 or 3 | Rework, back to that stage, Ready |
| parked | either | Parked, Stage 2, No action |
| rejected | either | Rejected, Stage 2, No action |

Only Claude Code and Codex rows are made Ready; Manual and Unassigned get No action. It also sets the item's Updated date and, if blank, the decision's Decision Date. The rules come from [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml); a unit test checks they agree.

- It acts only on items still Awaiting decision, using the decision named in Current decision ID, so a decision is never applied twice and old accepted decisions are never replayed. It keeps no state of its own.
- Proposed decisions are skipped. Problems (no Current decision ID, a decision for another item or stage, rework without instructions) are reported and that item is left unchanged.
- To change your mind after a decision was applied, edit the Pipeline row; editing the decision again does nothing.
- It runs every 10 minutes (`CHECK_EVERY_MINUTES`) and straight after a person edits the Decision Register. Edit triggers don't fire for API writes, so decisions written by an AI session are picked up by the timer.

Functions: `previewDecisions` (reports, writes nothing), `applyDecisions` (a preview while `ENABLE_WRITES` is false), `installTriggers`, `stopTriggers`. The same four are under **Extensions → Horology — Pipeline decisions**.

## Locations

Under **Extensions → Horology — Workbook** (the project was called Horology — Locations before it also held the item form):

- **Add Pipeline item:** a pop-up form for new Master rows, which stays open to add several. It fills the next ID, Created and Updated, and the capture values (Inbox, Stage 0, No action, Unassigned), or Stage 1 when the item is marked Ready; Domain comes from the Domains tab and Entity from that domain's entities, and the other dropdowns from Master's own.
- **Show folder structure:** a sidebar drawing the Locations tab as a collapsible tree, with Input and Output marked, a filter and links to each folder. Rows whose parent can't be found are listed separately rather than hidden.
- **Check folders against Drive:** opens each folder by the ID in its Location link and updates **Name** and **Parent** to match Drive. It reports folders that are trashed, can't be opened, moved out of the listed folders, or moved into another domain or entity, and lists subfolders in Drive that aren't in Locations as suggestions. The report opens at once with a progress message; the check itself takes a few seconds, reading all listed folders and their subfolders in batched Drive API queries (advanced Drive service, v3, including shared drives).

It reads Drive and the Locations tab, writes only Name and Parent cells, never adds rows, and never creates, moves or renames anything in Drive. Scopes: this spreadsheet, Drive read-only, and the sidebar and dialog. A row's parent is the row in the same Domain whose Name matches its Parent, in the same Entity, except that an Entity folder's parent is the Root folder.

## ClickUp Sync

Mirrors Pipeline items to ClickUp tasks through ClickUp's direct API (not its MCP), so ClickUp can serve as a review screen. Sheets stays the record: no field in Sheets is overwritten by a ClickUp title or description edit. Optional; with no `LIST_` properties nothing is mirrored.

### Lists and status mapping

A domain is mirrored when Script Properties has `LIST_<Domain>` set to a ClickUp list ID, with the domain spelled as on the Domains tab (matching to Pipeline rows ignores case). Several domains may share a list; there is one list per domain, not per entity. A domain without a list is reported as blocked and nothing is sent. Removing a property stops mirroring that domain; changing a domain's list stops its existing items with "Domain/list changed" until their tasks are moved by hand and their state reconciled, so tasks are never duplicated or moved automatically. `discoverClickUpLists` logs every list the token can reach.

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

Lists must keep the statuses `open`, `review`, `blocked`, `backlog`, `rejected` and `closed`.

### Decisions and review

Decisions made in Sheets are applied by Pipeline decisions, not this sync; while a decided item waits to be applied, the sync skips it.

With `ALLOW_CLICKUP_REVIEW` true, a task moved out of an established `review` baseline records a decision: `open` accepts the current proposal, `blocked` parks it, `rejected` rejects it. `closed` is not an approval and `backlog` is not rework; rework feedback goes in the Decision Register. One sync must have published the review before ClickUp changes count. ClickUp's API doesn't reliably say who changed a status, so the register records ClickUp as the source with the actor unavailable; enable this only for lists whose editors you trust.

### Tasks and comments

- **Descriptions** are owned by the mirror: a stable Pipeline marker (`[Welladino Pipeline <sheet ID>:<item ID>]`, kept as is so existing tasks still match), summary, target and branch, stage, links and review instructions. Put personal notes in comments.
- **Comments:** each Decision Register row becomes one complete comment, updated in place when the row changes. New decision rows add new comments. Personal comments are left alone and never read as instructions.
- **Existing tasks:** the sync finds tasks carrying the exact marker before creating new ones; duplicate markers or conflicting task IDs stop the item. Adopting a task without the marker (`ALLOW_ADOPT_EXISTING`) overwrites its description, so it's off by default.

### Selection and batching

The sync selects the configured pilot IDs, or every item when `SYNC_ALL` is true and the pilot list is empty, then checks each row before any write or ClickUp call:

- An unmanaged row with no Stage is skipped as incomplete.
- Invalid IDs or titles, unmapped domains, unsupported stages or statuses, inconsistent review links, pending writes and conflicting task links or list changes are blocked, with the reason logged. A managed row whose Stage was cleared is blocked, not skipped.
- Duplicate register IDs, missing headers and invalid Document Index data stop the whole run.
- Manual, Unassigned and No action rows are mirrored too; Ready is agent selection, not a sync gate.

Eligible rows are taken in Pipeline ID order, at most `MAX_ITEMS_PER_RUN` (5) attempts per run. A cursor in the state tab remembers the last ID and wraps around, so every eligible row gets its turn. Preview never moves the cursor or writes counts.

### Document counts and fields

Each synced row's Document count is refreshed from the Document Index: distinct Drive files listing that Pipeline ID (comma-separated IDs share a document). It counts indexed documents, not documents in the graph. `refreshDocumentCounts` refreshes every row without calling ClickUp.

`initializeSheets` adds, if missing: Pipeline **Stage**, **Review stage**, **Current decision ID**, **ClickUp Pipeline URL**, **Document count**; Decision Register **Pipeline ID**, **Review stage**, **Rework instructions**, **Review source**. ClickUp Pipeline URL is the only task link.

### State and failures

State lives in the Pipeline's **`_ClickUp Sync`** tab: task IDs, last synced statuses, the review snapshot, decision-comment IDs and hashes, and the cursor. It stays with the workbook, so a new project picks up where the old one left off. Don't edit it during a run.

- Both-side changes, a proposal changed during review, domain changes and invalid links pause the affected item. Nothing is deleted or moved automatically.
- Before creating a task or comment, a pending marker is saved. A timeout after submission leaves it pending rather than risk a duplicate on retry: check ClickUp, reconcile the ID in the state tab, then clear the pending marker.
- The run takes a lock, paces requests and logs IDs, actions and errors, never the token or bodies.
- Sheets and ClickUp have no shared transaction: avoid editing items while a sync runs, and after a partial failure check the log and records before retrying.

Public functions: `initializeSheets`, `previewSync` (ClickUp reads only; writes nothing), `applySync` (refused while `ENABLE_WRITES` is false), `installHourlyTrigger`, `stopSync`, `refreshDocumentCounts`, `discoverClickUpLists`.

| Module | Responsibility |
|---|---|
| Config.js | Behaviour settings, status mapping, token loading |
| Registers.js | Pipeline ID, register links and domain lists, from Script Properties and the Pipeline's tabs |
| Sync.js | Preview and apply entry points, locking, run limits |
| Eligibility.js | Row checks shared by batch selection and per-item sync |
| Tasks.js | Task matching, description, per-row coordination |
| Decisions.js | Review checks, approvals and rework |
| DecisionComments.js | One comment per decision row |
| ClickUpApi.js | API requests, pacing, pagination |
| Documents.js | Document Index lookup and counts |
| Sheets.js | Reading Master tables and writing single cells |
| SyncState.js | The `_ClickUp Sync` tab |
| Setup.js | Schema fields and the hourly trigger |
| Clickuplist.js | `discoverClickUpLists` |
| Utils.js | Normalisation and hashing |

## Tests

Each folder has offline tests (`npm test`) with fake sheets, Drive and ClickUp; nothing calls Google or ClickUp. They cover the decision rules and runs, the folder tree and Drive comparison and the Drive adapter's batching, and the sync's preview isolation, creation guards, review stages, rework, conflicts and comment de-duplication. They don't prove live permissions, list statuses or API behaviour: after publishing, run the preview in the live project.
