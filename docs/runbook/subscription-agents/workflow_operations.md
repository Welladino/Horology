# Operate the subscription-agent workflow

Read the [subscription-agent workflow](../../architecture/subscription-agents/workflow.md) for responsibilities and stages. This runbook covers routine operation and workflow maintenance; it does not deploy Hermes or the MCP services.

## Live records and instructions

Use the current workspace's **Registers** tab to open its Pipeline, Decision Register, Document Index and Agent Register. Use **Locations** in that Pipeline for Drive routing. Public documentation deliberately does not link a person's live workbooks. Their responsibilities are described in [Workspace records](../../architecture/subscription-agents/workspace-records.md).

## Change the workflow

Edit [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml) first, then the skills or Apps Script code that apply the changed rule, and the Mermaid diagrams in the [subscription-agent workflow](../../architecture/subscription-agents/workflow.md). Then check:

```bash
.venv/bin/python -m pytest tests/unit/workflow -q
```

The tests fail if a move or status in `workflow.yaml` is missing from the diagrams.

## Run Ready items

Set the item's Agent status to Ready, Agent type to Claude Code or Codex, and Run location to Local or Cloud (blank means Local). Then, in a Claude Code or Codex session opened in the Horology repository:

> Use horology-supervisor to run the Ready items.

or for one item:

> Use horology-supervisor to run Pipeline item 42.

The supervisor claims each item through the document graph and starts one session per item. Check progress by asking a session to `list_runs`, or `get_item_history` for one item. Every run needs the document-graph connector. Claude cloud runs need the skills and the document graph and Google connectors on your claude.ai account. Codex runs need the Codex CLI installed and signed in.

Feature, Enhancement, Refactor and Fix items take the implementation route: one run writes the plan document to Drive and the steps on the Steps tab, moves the item to Stage 3 and implements it, with Status In progress until it finishes. It ends Completed at Stage 4 with an **Implementation report** Google Doc (what changed and why, commits and pull request, tests, changes from the plan and what's left for you, including deploy steps) and a Stage 4 page made from it, both in the Document Index, or Awaiting decision with an Implementation question for you to answer below. If an implementation run fails, the item stays In progress with Agent status No action; set it Ready again to retry.

## Decide on an item

Open **Extensions → Horology — Pipeline decisions → Open Horology workspace** from your Pipeline workbook and follow its private web-app link while signed into the owning Google account. In **Decisions**, expand a Pipeline row and open a decision to compare the options and evidence and choose an outcome. For a different option, edit **Decision to record** so its conditions are accurate, then give a short reason. **Save decision** writes to Decision Register Master and applies that item's Pipeline transition immediately; the page reports if the Pipeline update is pending.

```mermaid
flowchart LR
  open["<b>Open Decisions</b><br/>Choose the item waiting<br/>for your review"]
  read["<b>Read the evidence</b><br/>Compare the deliverable,<br/>synthesis and recommendation"]
  choose{"<b>Choose an outcome</b>"}
  accepted{"<b>Accepted</b><br/>What was reviewed?"}
  proposal["<b>Investigation proposal</b><br/>Approved · Stage 3 · Ready<br/>for the detailed deliverable"]
  complete["<b>Specialist deliverable</b><br/>Stays Completed · Stage 4<br/>No action"]
  resume["<b>Implementation question</b><br/>In progress · Stage 3 · Ready<br/>implementation resumes"]
  rework["<b>Rework</b><br/>Add clear instructions<br/>Item returns to Ready"]
  parked["<b>Parked</b><br/>No action until its<br/>revisit trigger applies"]
  rejected["<b>Rejected</b><br/>No further action"]
  saved["<b>Saved</b><br/>Decision Register keeps the review;<br/>Pipeline receives the transition"]

  open --> read --> choose
  choose -->|Accept| accepted
  accepted --> proposal
  accepted --> complete
  accepted --> resume
  choose -->|Request changes| rework
  choose -->|Later| parked
  choose -->|Stop| rejected
  proposal --> saved
  complete --> saved
  resume --> saved
  rework --> saved
  parked --> saved
  rejected --> saved

  classDef action fill:#e8f0fe,stroke:#1a73e8,color:#174ea6
  classDef decision fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef success fill:#e6f4ea,stroke:#137333,color:#137333
  classDef revise fill:#fce8e6,stroke:#c5221f,color:#a50e0e
  classDef neutral fill:#f1f3f4,stroke:#5f6368,color:#202124
  class open,read,saved action
  class choose,accepted decision
  class proposal,complete,resume success
  class rework revise
  class parked,rejected neutral
```

Use **Pipeline** to browse all Master rows as Cards or Rows. Search the text or filter by Domain and Status. Expand **More filters** for Entity, Type, Agent status, Agent type, Run location and Stage; **Clear filters** resets the search and filters. Open an item to see its next step, revisit trigger and links. Choose **Edit item** to change its title, type, summary, next step, revisit trigger or agent assignment, then **Save item**. Domain, Entity, Status and Stage are displayed without edit controls. If another writer changed the item, refresh it before saving.

In **Decisions**, expand a Pipeline item to see its decisions, then choose a decision to review it or read its recorded outcome and reason.

An item is **Completed** as soon as its Stage 3 run saves the deliverable (on the implementation route, the Implementation report) and the Stage 4 synthesis or page. Its Specialist deliverable decision still appears under **Needs review**. **Keep completed** accepts it and changes nothing. Rework, park or reject reopen the item; rework sends an implementation back to Stage 3 with your instructions.

To change a decision that was already applied (for example an Approved item you now want to park), open it under **Decision history**. **Revise this decision** is shown when it is the item's current decision and no run or review is open (the item is Approved, Rework, Parked, Rejected or Completed). Choose the new outcome, give a reason (rework: the instructions), and **Revise decision**. The decision keeps its ID, your reason is added to it, and the Pipeline item moves straight away. If the item is Researching or In progress, wait for the run to finish.

To capture new work, choose **Add Pipeline item** in the same page. Fill Title and Domain, then optionally add the reason, next step, revisit trigger and target. Ready items need an agent and a Next step. **Add item** writes the next permanent ID to Pipeline Master. The old Add Pipeline item entry is no longer in the Workbook Extensions menu.

The existing sheet route also works: in the Decision Register, set the current decision's Status to accepted, rework (with Rework instructions), parked or rejected. A direct human edit is applied by the installable edit trigger when it is present. Apps Script or API writes must call `applyDecisions` explicitly. To check, inspect the item's Status in the Pipeline or run `previewDecisions` from the Apps Script editor as an administrator.

## Scheduled jobs

Create the oversight jobs below on a platform scheduler. Investigation and Stage 3 runs remain founder-started. During a Stage 3 run, the supervisor invokes Horology Synthesis Artifacts immediately after saving the deliverable, proposes a Specialist deliverable decision and sets the item Completed at Stage 4. No Stage 4 schedule or second founder prompt is needed.

| Job | When | Prompt |
|---|---|---|
| Digest | Daily | `Use horology-digest to write today's Horology digest.` |
| Planner | Daily, or on request | `Use horology-planner to plan the Pipeline items set to Plan.` |

The scheduled session needs the skills (claude.ai skills for Claude, the installed plugin for Codex) and Drive, Docs and Sheets access. An empty Plan list means the planner run ends quickly.

## Maintain ClickUp integration

Use the [Apps Script runbook](clasp.md) to connect, compare and publish the Apps Script projects and set up ClickUp Sync. The [Apps Script architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md) describes decision rules, the Drive check, and one-way ClickUp status and milestone comments.
