# Subscription agents

Subscription agents are Horology's document-driven way of working. Claude, ChatGPT and Codex sessions, run on personal AI subscriptions, do research, assessment and planning by following versioned skills and writing their results to Drive and Sheets. They don't use Hermes, its profiles or kanban.

![Subscription-agent workflow](../diagrams/subscription_workflow.svg)

## Components

| Component | Role | Where it lives |
|---|---|---|
| Workflow guides and Agent Location Directory | Instructions, output destinations, presentation rules | Drive `01_Welladino/00_Guides` |
| Pipeline | Work queue: stage, scope, selection and status | Sheets in `01_Registers` |
| Decision Register | Founder decisions, evidence and rework instructions | Sheets in `01_Registers` |
| Document Index | Which documents belong to which item, revisions, supersedes, Graph Inclusion | Sheets in `01_Registers` |
| Agent Register | Agents, their platforms and prompt sources | Sheets in `01_Registers` |
| Templates | Document structure and visual assets | Drive `02_Templates` |
| Deliverables | Research, direction, plans and assessments | Domain or entity folders from the Location Directory |
| Skills | Versioned agent instructions | `plugins/horology-workflows/skills/` |
| Agent prompts | Research and Technical Assessment personas | `personas/subscriptions/` |
| ClickUp sync | Mirrors register rows to ClickUp tasks, statuses and decision comments | `google_appscript/clickup-sync/` (Apps Script) |

Sheets is the operational record and Drive holds the detailed deliverables; ClickUp is only a review screen. The repository versions the skills and the sync code; it is not a copy of Drive or Sheets.

## Stages

- **Stage 0, capture.** `welladino-capture-triage` records an idea, parked proposal or research request as a Pipeline row and checks for duplicates.
- **Stage 1, investigation and proposal.** The question decides the form: research (`welladino-research`), direction, a plan, or a technical assessment (`welladino-technical-assessment`). These are not a fixed sequence. The deliverable is saved to Drive and listed in the Document Index.
- **Stage 2, founder decision.** Approve, rework, park or reject, recorded in the Decision Register with feedback.
- **Stage 3, specialist deliverable.** An approved scope becomes a detailed deliverable, then review. For code work this is a planning note in the repository, not automatic implementation.

Stage and Review stage are separate fields, so a review can be told apart even when ClickUp statuses overlap.

## IDs and records

The Pipeline's permanent numeric ID joins decisions and documents; each register has its own numeric sequence. One Pipeline item can have several documents and several decision revisions. `Supersedes` marks a genuine replacement, not every related document. External IDs, ClickUp task URLs and Drive file IDs keep their own purposes.

## Selecting and running agents

`Agent status = Ready` marks the next bounded step for an AI agent; `Agent type` names the intended platform; `Manual` means founder-led. A session starts because the founder asks, or because a schedule was set up on the agent platform; a sheet value alone launches nothing. The agent reads the current Drive instructions, the Pipeline row and the relevant skill, then saves its output and updates the registers.

There is no scheduler or multi-writer coordination here: use one writer at a time until ID allocation and work claiming are coordinated.

## ClickUp sync

Apps Script syncs records; it never runs AI. Before each bounded batch it checks every selected Pipeline row: unmanaged blank-stage captures are skipped, invalid or conflicting rows are reported as blocked, and only eligible rows count against the batch. Eligible rows rotate by Pipeline ID, with the position kept in `_ClickUp Sync`. Preview changes nothing. The ClickUp token is kept only in Apps Script Script Properties; the repository holds sheet and list IDs, not credentials. Details: [`WORKFLOW.md`](../../../google_appscript/clickup-sync/WORKFLOW.md).

## Domains

Pipeline and the registers cover Welladino, Article Aggregator, Newsletter, Ecommerce and Horology, spelled as in the sheet's dropdowns. Horology maps to ClickUp list `901820246905` in `DomainLists.js` and has no Entity. Repository access and Drive destinations are configured separately; the agent checks both before working.

## Plugins and tools

| Plugin | Brings |
|---|---|
| `horology-workflows` | The three workflow skills. Drive, Docs, Sheets and ClickUp come from the user's own connectors. |
| `horology-document-graph` | The document-graph connector and its skill: search before starting, write findings that have no Drive document |
| `horology-tools` | The gateway connector and its skill: Supabase metadata, Tavily, Firecrawl |

Drive plus a Document Index row stays the main record for a finished deliverable. Rows with Graph Inclusion TRUE are copied into the document graph by the [sync job](../mcp/document-graph.md#document-index-sync), so later sessions can find them. Installing and validating the plugins: [Claude plugins runbook](../../runbook/subscription-agents/claude_plugins.md).

Native platform connectors (GitHub, Drive and so on) are outside the gateway's policy and budgets. Permission to research does not authorise code changes.
