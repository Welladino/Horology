# Execution history in Neon, and fewer Pipeline tabs

## Topic
- execution-history-in-neon

## Question
- Where should run, step and status-change history live, how does it get filled, and how much should AI agents write themselves?

## Summary
- **Sheets is where the founder edits and decides; Neon holds the machine history.** The Runs, Steps and five domain tabs are removed; the Pipeline workbook keeps Master, Read Me, `_ClickUp Sync` and Migration archive.
- **The system records the facts; the AI makes two calls per run.** `claim_item` (atomic claim, creates the run) and `finish_run` (outcome, skills used, notes, marked self-reported). Status changes, outputs, decisions and times are derived by the sync job from the sheets.
- **The workflow stays a file.** `workflow.yaml` remains the definition; the document-graph image carries it so tools can check values and flag unexpected moves.

## Sources
- [Supervisor and runs brief](2026-10-16_subscription-agent-supervisor-and-runs_research.md) (Runs tab, claims, planner, digest).
- `workflow.yaml`: `plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml`.
- Existing schema: `documents` (workspace, source, `index_document_id`, `pipeline_id`), `graph_runs` (one run per workspace with a claim token), unused `run_log` (agent, goal, summary, one `document_id`).
- Document Index headers (live, 2026-10-16): Document ID, Pipeline item, Sequence, Title, Drive URL, Workspace, Domain, Entity, Document Type, Document Status, Last Updated, Graph Inclusion, Graph Sync Status, Graph Document ID, Last Synced Revision, Related ClickUp URL, Related Repo Document, Related Pipeline URL, Supersedes document ID, Pipeline ID.

## Findings

- **Tabs were multiplying.** Runs, Steps and a planned Events tab are machine records the founder never edits. Kept in Sheets they add clutter and give weak guarantees (a claim written to a cell and read back can race).
- **AI-written history is self-reported.** Agents can skip a call, report outputs they didn't save, or differ by platform. Narrow tools with server-set IDs and times limit this but don't remove it.
- **Most facts don't need the AI.**
  - Status changes: comparing successive copies of Master catches every change, whoever made it; a change during an active run is attributed to that run.
  - Outputs: Document Index rows for the item that appear or change during the run window, plus agent documents (`write_document`) with that Pipeline ID.
  - Decisions: the Decision Register. Times: the claim and the status changes.
- **Only two facts need the session:** the claim (before work starts; there is no dispatcher script) and how the run ended and why.
- **`documents` is the knowledge store, not an output list.** Sheet documents enter it only with Graph Inclusion TRUE and leave when it's turned off; digests never enter. Run outputs must therefore come from a copy of the whole Document Index. The two join on Document ID = `documents.index_document_id`.
- **A workflow table isn't needed yet.** The rules are read by skills, the Apps Script sync and reviewers; a versioned file suits them. A table would only help if the workflow were edited without a release or joined in SQL.
- **`run_log.document_id`** holds one document; a run has several outputs, so outputs move to a link table.

## Recommendation

**Sheets.** Remove the Runs, Steps and five domain tabs (the founder filters Master's table instead). The planner writes steps as a numbered list in Next step.

**Neon tables** (all workspace-scoped):

| Table | New or changed | Filled by |
|---|---|---|
| `pipeline_items` | New | Records pass: snapshot of Pipeline Master |
| `pipeline_events` | New | Records pass: differences between snapshots, attributed to the active run if any |
| `decisions` | New | Records pass: Decision Register |
| `document_index` | New | Records pass: every Document Index row (details only, no content) |
| `run_log` | Extended | `claim_item` and `finish_run` |
| `run_outputs` | New | Records pass: the item's Index rows and agent documents during the run window |

**Document-graph tools.**

| Tool | Does |
|---|---|
| `claim_item(pipeline_id, agent_type, run_location, kind)` | Atomically claims the item for 2 hours (refuses a live claim) and returns the run ID |
| `finish_run(run_id, status, skills_used, steps_done, notes)` | Records the outcome; self-reported fields are labelled so |
| `list_runs(since)` | Runs started or finished since a time, for the digest |
| `get_item_history(pipeline_id)` | The item, its runs, events, decisions and outputs in date order, with each event marked expected or unexpected by `workflow.yaml` |

The server sets run IDs, timestamps, expiry and workspace.

**Sync job.** A records pass that needs no AI or embeddings: reads Pipeline Master, the Decision Register and the Document Index; upserts the copies; records events; links run outputs. It runs with every sync and alone with `GRAPH_SYNC_MODE=records`. The workbook map grows from a Document Index ID to the three spreadsheet IDs per workspace. The job's service account needs Viewer on the Pipeline workbook and the Decision Register.

**Skills.** The supervisor and planner claim with `claim_item` and end with `finish_run`; the digest reads `list_runs` and `get_item_history`; record rules drop the Runs and Steps tabs.

**Order.** Migration → core domain and tools with tests → records pass → skills and docs → remove the tabs (after the founder approves the exact change) → deploy (migrate Neon, build, update service and job, share the two sheets).

## Open Questions
- Snapshot comparison sees only the state at each sync; several changes between two syncs appear as one. Running a records sync at the start and end of each run (the tools can request it) narrows that.
- Events from founder edits are labelled "founder or sync": the sheets don't say who edited a cell.
- How long to keep snapshots and events (no retention limit is set yet).
