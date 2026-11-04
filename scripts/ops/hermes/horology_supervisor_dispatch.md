# Hermes dispatch adapter

This adapter is installed for Hermes Coordinator and Operator. It handles only
Pipeline Agent type **Hermes**. The sheet value is authoritative: do not route
Claude Code, Codex, ChatGPT Work, Manual or Unassigned rows through Hermes.
Hermes rows are **Local** only.

Hermes separates dispatch from execution:

- **Coordinator** runs supervisor dispatch and status modes. It has read-only
  Pipeline and document-graph access, creates Kanban tasks, and never calls
  `claim_item`, changes a Pipeline row or writes a deliverable.
- **Operator** runs item mode. It calls `claim_item` with `agent_type: "Hermes"`,
  `run_location: "Local"` and `kind: "run"` when the task has no run ID. It owns
  the run's Sheets and Drive writes, specialist work, final verification and
  `finish_run` call.
- **Explorer** performs repository and test steps in its isolated environment.
  It never owns the Pipeline run or writes the workspace records.

## Dispatch with Kanban

For each Ready Hermes row, Coordinator creates exactly one initial Kanban task
assigned to `operator`. Do not claim the row first. Give the task the
self-contained prompt:

> Use the horology-supervisor skill in item mode for Pipeline item `<ID>`. No
> run ID has been assigned; claim it as Hermes/Local before changing anything.

Include the row's bounded next step, target fields and acceptance criteria.
Pass `skills: ["horology-supervisor"]`. A second task for the same item is safe:
Operator must stop when `claim_item` returns `claimed: false`.

Record the Kanban task and run identifiers when Operator reports them. A Kanban
task is not a run claim and must never be presented as one.

## Implementation-route code steps

Operator plans the item, writes the Stage 1 document and Steps rows, and returns
the active run ID plus a bounded code-task specification when an open step
requires repository work. Coordinator then:

1. creates an `explorer` Kanban task for those code steps, with the repository,
   base revision, branch, tests, delivery boundary and acceptance criteria;
2. uses `parents` so Explorer waits for the Operator planning task;
3. after Explorer returns branch, commits, tests and pull-request evidence,
   creates an `operator` continuation task with both earlier tasks as parents,
   the same Pipeline ID and run ID, and instructions to verify the evidence,
   finish the open Steps, write the Implementation report and call `finish_run`.

Do not give Explorer Google Workspace credentials or ask it to finish the run.
Do not let Operator invent code results. If a dependent task fails, Coordinator
creates no success continuation; Operator records the failure or recoverable
state according to item mode.

## Monitoring and status

Use Kanban state for live Hermes task progress and the supervisor's status mode
for durable run history. Coordinator may call the document graph's read-only
`list_runs` and `get_item_history`; it must not use write tools. Report running,
finished, failed and founder-attention items as the supervisor requires.

The live end-to-end implementation path requires Explorer's founder-provided
GitHub hook, and status mode requires Coordinator's founder-provided read-only
document-graph connection. Tests may verify the routing contract without those
credentials; never weaken the adapter or copy credentials into a Kanban task.
