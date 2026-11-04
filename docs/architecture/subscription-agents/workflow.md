# Subscription-agent workflow

Subscription agents are Horology's document-driven way of working. Claude, ChatGPT and Codex sessions, run on personal AI subscriptions, do research, assessment and planning by following versioned skills and writing their results to Drive and Sheets. They don't use Hermes, its profiles or kanban.

The workflow's states, field values and allowed moves are defined once in [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml). The skills and Apps Scripts follow it, and unit tests check that they remain aligned.

## Routes

An item's **Type** chooses its route ([`routes`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml) in `workflow.yaml`):

| Route | Types | Stages | Status while a run works |
| --- | --- | --- | --- |
| Investigation | Idea, Research, Direction, Plan | Stage 1 proposal (Drive document and Steps rows) → Stage 2 founder decision → Stage 3 deliverable → Stage 4 synthesis → Completed (reopenable from its decision) | Researching |
| Implementation | Feature, Enhancement, Refactor, Fix | Stage 1 plan (Drive document and Steps rows) → Stage 3 implementation and Implementation report → Stage 4 page → Completed (reopenable from its decision); no Stage 2 | In progress |

The implementation route was decided by the founder on 29/10/2026 ([note](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-10-29_implementation-route_note.md)). The run writes its plan document to Drive and its steps as Steps rows, moves the item to Stage 3 itself and implements in the same run. When no founder decision is needed it writes an **Implementation report** Google Doc from its template (what changed and why, commits and pull request, tests, changes from the plan, what's left for the founder), makes a Stage 4 page from the report through Horology Synthesis Artifacts, proposes a Specialist deliverable decision and finishes **Completed** at Stage 4, as the founder decided on 04/11/2026 ([note](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-11-04_stage-1-document-and-implementation-report_note.md)). Implementations finished before then ended Completed at Stage 3. When a run needs a founder choice, it stops at **Awaiting decision** with Review stage **Implementation question** (a proposed decision with Options rows whose Research Links name the Stage 1 document, reviewed on the decision page); the founder's answer resumes the item at Stage 3, In progress and Ready for its platform.

Every route's Stage 1 writes a specialist document in Drive (Research, Direction, Plan or Technical Assessment template) plus Steps rows, so the founder can read what was planned and done without asking an agent. The Docs are the record; Stage 4 pages are viewing copies and don't enter the document graph. Graph Inclusion on the Document Index stays the founder's: agents add rows with it FALSE and never change it.

## Status lifecycle

The first diagram shows the investigation route in human terms, the second the implementation route. The table beneath it is the exact maintainer reference, including less common direct park, reject and reopen moves and the revise move, drawn once as a dotted line.

```mermaid
flowchart LR
  %% Exact workflow moves represented by this lifecycle and the table below:
  %% capture, start-run, submit-for-review, synthesize-stage-3, accept-stage-1,
  %% accept-stage-3, rework, park, decide-park, unpark, reject, decide-reject, reopen, revise
  %% Investigation route: Idea, Research, Direction and Plan items.
  inbox["Inbox<br/>Stage 0"]
  investigate["Researching<br/>Stage 1 investigation"]
  review1{"Awaiting decision<br/>Stage 2 review"}
  approved["Approved<br/>Stage 3 is Ready"]
  specialist["Researching<br/>Stage 3 deliverable<br/>and Stage 4 synthesis"]
  completed["Completed<br/>Stage 4, its Specialist<br/>deliverable decision open"]
  rework["Rework<br/>Instructions required"]
  parked["Parked<br/>No action"]
  rejected["Rejected<br/>No action"]

  inbox -->|Start selected work| investigate -->|Submit proposal| review1
  review1 -->|Accept proposal| approved --> specialist -->|Save both outputs| completed
  completed -->|Accept deliverable · no change| completed
  review1 -->|Request changes| rework
  completed -->|Reopen · request changes| rework
  rework -->|Run again| investigate
  review1 -->|Do later| parked
  completed -->|Reopen · do later| parked
  parked -->|Revisit| inbox
  review1 -->|Stop| rejected
  completed -->|Reopen · stop| rejected
  rejected -->|Reopen| inbox
  approved -.->|revise · change a decided decision| parked

  classDef waiting fill:#f1f3f4,stroke:#5f6368,color:#202124
  classDef running fill:#f3e8fd,stroke:#9334e6,color:#681da8
  classDef decision fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef success fill:#e6f4ea,stroke:#137333,color:#137333
  classDef revise fill:#fce8e6,stroke:#c5221f,color:#a50e0e
  class inbox,parked,rejected waiting
  class investigate,specialist running
  class review1 decision
  class approved,completed success
  class rework revise
```

```mermaid
flowchart LR
  %% Implementation route: Feature, Enhancement, Refactor and Fix items. Exact moves:
  %% start-implementation, plan-implementation, complete-implementation, raise-implementation-question,
  %% resume-implementation, run-failed (Status stays; Agent status back to No action)
  inbox2["Inbox<br/>Stage 0"]
  planning["In progress<br/>Stage 1 plan document<br/>and Steps rows"]
  implementing["In progress<br/>Stage 3 implementation<br/>and Implementation report"]
  question{"Awaiting decision<br/>Implementation question"}
  done["Completed<br/>Stage 4 page, its Specialist<br/>deliverable decision open"]
  rework2["Rework<br/>Stage 3"]
  stopped["Parked or Rejected<br/>Stage 3 or Stage 4"]

  inbox2 -->|Start selected work| planning -->|Plan written; same run| implementing
  implementing -->|Report and page saved; same run| done
  done -->|Accept · no change| done
  done -->|Reopen · request changes| rework2
  done -->|Reopen · do later or stop| stopped
  planning -->|Needs a founder choice| question
  implementing -->|Needs a founder choice| question
  question -->|Answer · Ready again| implementing
  question -->|Request changes| rework2 -->|Run again| implementing
  question -->|Do later or stop| stopped

  classDef waiting fill:#f1f3f4,stroke:#5f6368,color:#202124
  classDef running fill:#f3e8fd,stroke:#9334e6,color:#681da8
  classDef decision fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef success fill:#e6f4ea,stroke:#137333,color:#137333
  classDef revise fill:#fce8e6,stroke:#c5221f,color:#a50e0e
  class inbox2,stopped waiting
  class planning,implementing running
  class question decision
  class done success
  class rework2 revise
```

| Move ID | From → To | Who/what makes it | Meaning |
| --- | --- | --- | --- |
| `capture` | New → Inbox | Capture skill | Record a Stage 0 item; do not run it |
| `start-run` | Inbox, Rework or Approved → Researching | Supervisor | Begin the selected Stage 1 or Stage 3 work of an investigation-route item |
| `start-implementation` | Ready → In progress | Supervisor | Begin an implementation-route item: plan at Stage 1, or implement at Stage 3 |
| `plan-implementation` | In progress, Stage 1 → Stage 3 | Supervisor | The plan document is in Drive and the steps on the Steps tab; implement in the same run |
| `complete-implementation` | In progress, Stage 3 → Completed, Stage 4 | Supervisor and synthesis specialist | Every step Done or Skipped, no founder decision needed, the Implementation report and Stage 4 page saved, and a Specialist deliverable decision proposed as the Current decision ID |
| `raise-implementation-question` | In progress → Awaiting decision, Stage 3 | Supervisor | Stop with a proposed decision and Options rows (Review stage Implementation question) |
| `resume-implementation` | Awaiting decision → In progress, Stage 3 | Founder or decision sync | The founder answered the Implementation question; Ready again for its platform |
| `run-failed` | Researching or In progress (Agent status → No action) | Supervisor | The run failed or was released; Status stays and the run's notes say why |
| `submit-for-review` | Researching → Awaiting decision | Supervisor | Submit a Stage 1 investigation for Stage 2 review |
| `synthesize-stage-3` | Researching → Completed, Stage 4 | Supervisor and synthesis specialist | Save the Stage 3 deliverable and Stage 4 synthesis, and propose a Specialist deliverable decision as the Current decision ID |
| `accept-stage-1` | Awaiting decision → Approved | Founder or decision sync | Accept the investigation; make Stage 3 Ready |
| `accept-stage-3` | Completed → Completed (or Awaiting decision → Completed for items that reached Stage 4 before 03/11/2026) | Founder or decision sync | Accept the specialist deliverable; nothing changes |
| `rework` | Awaiting decision, or Completed with an open Stage 4 review → Rework | Founder or decision sync | Save instructions and make the item Ready again (Stage 1 for an Investigation proposal, Stage 3 otherwise) |
| `park` | Inbox or Rework → Parked | Founder | Stop before review and retain the item |
| `decide-park` | Awaiting decision, or Completed with an open Stage 4 review → Parked | Founder or decision sync | Park during a review |
| `unpark` | Parked → Inbox | Founder | Return a parked item to the queue |
| `reject` | Inbox or Parked → Rejected | Founder | Reject outside a review |
| `decide-reject` | Awaiting decision, or Completed with an open Stage 4 review → Rejected | Founder or decision sync | Reject during a review |
| `reopen` | Rejected → Inbox | Founder | Return a rejected item to the queue |
| `revise` | Approved, Rework, Parked, Rejected or Completed → any of those | Founder or decision page | Change the item's current, already applied decision (for example Approved → Parked); the item moves as the new outcome would from review |

## Agent selection

Agent status is separate from workflow status. It answers whether an agent should act next:

```mermaid
flowchart LR
  noaction["No action"]
  plan["Plan"]
  ready["Ready"]
  noaction -- "request-plan · founder" --> plan
  plan -- "planned · planner · Planner output Yes" --> noaction
  noaction -- "select · founder · Stage 1 or 3, Claude Code or Codex rows" --> ready
  noaction -- "accept-stage-1, resume-implementation or rework · decision sync" --> ready
  plan -- "select · founder" --> ready
  ready -- "submit-for-review, synthesize-stage-3, complete-implementation, raise-implementation-question or run-failed · supervisor" --> noaction

  classDef inactive fill:#f1f3f4,stroke:#5f6368,color:#202124
  classDef planning fill:#fef7e0,stroke:#f9ab00,color:#7a4f01
  classDef selected fill:#e8f0fe,stroke:#1a73e8,color:#174ea6
  class noaction inactive
  class plan planning
  class ready selected
```

A run (`start-run` or `start-implementation`) only starts on a Ready row; the decisions script sets Ready again after accept-stage-1, resume-implementation and rework, and No action after the other decisions. An implementation-route item left In progress by a failed or stopped run can be selected again.

## Stages

* **Stage 0, capture.** `horology-capture-triage` records an idea, parked proposal or research request as a Pipeline row and checks for duplicates.
* **Stage 1, investigation and proposal (investigation route).** The question decides the form: research (`horology-research`), direction, a plan, or a technical assessment (`horology-technical-assessment`). These are not a fixed sequence. The deliverable is saved to Drive and listed in the Document Index, and the run's steps are written as Steps rows when none are open.
* **Stages 1, 3 and 4, implementation route.** Feature, Enhancement, Refactor and Fix items: the run writes the implementation plan to Drive (Plan template, or a technical assessment when options must be compared first) and as Steps rows (Stage 1), moves the item to Stage 3 itself, implements it (code on a branch with a pull request, or the named change) and marks each step Done. It then writes the Implementation report Google Doc, saved beside the Stage 1 document, and the Stage 4 page made from it, proposes a Specialist deliverable decision and finishes Completed at Stage 4. A founder choice it needs becomes an Implementation question. There is no Stage 2.
* **Stage 2, founder decision.** Approve, rework, park or reject, recorded in the Decision Register with feedback; options come from its Options tab. A decision already applied can later be revised from the decision page. The Horology web workspace applies the decision immediately; direct edits in the register can be handled by its edit trigger.
* **Stage 3, specialist deliverable.** An approved scope becomes a detailed deliverable. On the investigation route, code work is a planning note in the repository, not implementation; implementation belongs to the implementation route.
* **Stage 4, synthesis.** In the same Stage 3 run, the supervisor calls Horology Synthesis Artifacts to turn the investigation and specialist deliverable (on the implementation route, the Implementation report) into a concise visual briefing. HTML is preferred when it can be saved and opened reliably; a visual Doc or Sheet can be used when better suited. The supervisor proposes a Specialist deliverable decision (accept, rework, park), makes it the Current decision ID and sets the item **Completed** at Stage 4, as the founder decided on 03/11/2026 (Decision 15). No new prompt, selection or schedule is needed for synthesis.

Stage and Review stage are separate fields. At Stage 2 the founder reviews the Investigation proposal; at Stage 4 the item is already Completed and the founder reviews the Specialist deliverable (or the implementation and its report) alongside its synthesis when convenient; on the implementation route, at Stage 3, the founder answers an Implementation question.

An item's review is **open** (`open_review` in `workflow.yaml`) while it is Awaiting decision, or Completed at Stage 4 with Review stage Specialist deliverable. Its current proposed decision can be decided only then. At Stage 4, accepting changes nothing, and rework, park or reject reopen the item. Items 45 and 53 reached Stage 4 before this rule and still name their Stage 2 decision; they have no open review, and revising that decision would move them as an Investigation proposal outcome (back to Approved, Stage 3).

## IDs and records

The Pipeline's permanent numeric ID joins decisions and documents; each register has its own numeric sequence. One Pipeline item can have several documents and several decision revisions. `Supersedes` marks a genuine replacement, not every related document. External IDs, ClickUp task URLs and Drive file IDs keep their own purposes.

## Selecting and running agents

`Agent status = Ready` marks the next bounded step for an AI agent; `Agent type` names the intended platform; `Manual` means founder-led. A sheet value alone launches nothing.

Investigation and Stage 3 runs are started by the founder, from a session: in Claude Code or Codex, "run the Ready items" or "run item 42". Stage 4 runs automatically within the Stage 3 session. The **supervisor** (`horology-supervisor`) has three modes:

*   **Dispatch:** finds rows with Agent status Ready whose **Agent type** is the platform it's running on (Claude Code or Codex; each platform runs only its own rows), claims each with `claim_item` (2-hour claim), and starts **one session per item** according to the row's **Run location**:

    | Agent type  | Local        | Cloud              |
    | ----------- | ------------ | ------------------ |
    | Claude Code | `claude -p`  | `claude --cloud`   |
    | Codex       | `codex exec` | `codex cloud exec` |

    Where shell commands aren't available (for example claude.ai chat), it runs the items itself, one at a time.
* **Item:** handles exactly one item. It reads the row, decision feedback, any planned steps and the document graph; chooses specialist skills (`horology-specialists`); runs them as subagents; checks the results; and finishes the run. Specialist skills save their own Drive outputs, Document Index rows and proposed decisions.
* **Status:** read-only. Asked "what's happening?" or "what did item 42 find?", it reports running, finished (with key findings), failed and died runs, and what's waiting on the founder, from `list_runs`, `get_item_history` and the saved outputs. The founder talks to the supervisor instead of each session. It can't see progress inside a running session or steer one; that needs the session link.

One session per item keeps each supervisor's context to a single item, and lets its specialists run as subagents (subagents can't start their own).

| Pipeline field | Values                                                                    |
| -------------- | ------------------------------------------------------------------------- |
| Agent status   | No action, **Plan** (asks the planner to scope or split the item), Ready  |
| Agent type     | Claude Code, Codex, Manual (founder-led, never run by agents), Unassigned |
| Run location   | Local or Cloud; blank means Local                                         |
| Planner output | Yes or No; Yes when the planner has written a sharper question or steps   |

Runs are recorded in Neon, not in the workbook. Each run makes two document-graph calls: `claim_item` at the start (a 2-hour claim, so two sessions never take the same item) and `finish_run` at the end. Specialists reserve each new Decision or Document ID with `reserve_id` and call `check_register_write` before each register write, so parallel runs can't take or overwrite each other's rows ([register IDs](../mcp/document-graph.md#register-ids)). Status changes, outputs and decisions are recorded from the sheets by the sync job's records pass, and read back with `list_runs` and `get_item_history` ([execution history](../mcp/document-graph.md#execution-history)). Planned steps are rows on the Pipeline's Steps tab (older items: a numbered list in Next step); the item's session works through them in order and marks each one Done. Rules: the supervisor skill's [runs reference](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-supervisor/references/runs.md). To see one domain, use the Master table's filter.

Claude sessions, cloud and local, load the skills and connectors from the founder's claude.ai account, whatever repository they clone; plugins don't load in cloud sessions ([note](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-10-17_claude-skills-and-connectors-on-claude-ai_note.md)). Codex loads the skills from its plugins.

**Scheduled oversight** does no item work. The **digest** (`horology-digest`, daily) writes a Google Doc report card: counts by status, what finished with key findings and recommendations, what's waiting on the founder, and health and graph checks. The **planner** (`horology-planner`) acts only on rows set to Plan: it rewrites Next step as a bounded question, or writes the item's steps on the Steps tab with a one-line Next step, sets Planner output to Yes and Agent status back to No action; the founder then marks the item Ready. Both run on any platform's scheduler or on request. Design and options considered: [supervisor and runs brief](https://github.com/Welladino/Horology/blob/main/docs/planning/research/2026-10-16_subscription-agent-supervisor-and-runs_research.md).

## Related pages

- [How Horology works](../../runbook/setup/how-horology-works.md) — the non-technical walkthrough of one item from capture to decision.
- [Workspace records](workspace-records.md) — Pipeline tabs, registers, configurable domains and Drive routing.
- [Apps Script](apps-script.md) — decision application, the private workspace UI and optional ClickUp sync.
- [Workspace data flow](../data/workspace-data-flow.md) — what reaches Sheets, Drive and Neon, and when.
- [Skills and how to use them](../../runbook/setup/skills.md) — workflow and specialist capabilities.
- [Operate the workflow](../../runbook/subscription-agents/workflow_operations.md) — commands and procedures for running and maintaining it.
