---
name: horology-coordinator
description: Orient the user on Horology Pipeline work from the document graph, identify the right specialist skill for a bounded question, and report what Hermes can do with its currently connected tools. Use for Pipeline status and task-routing questions in Hermes.
---

# Horology coordinator

This skill runs in Hermes's Coordinator profile. The other Horology skills are
specialist instructions, not persistent profiles. Do not use Horology's retired
workflow persona-dispatch system; use Hermes Kanban for profile execution.

In the shared `workflow.yaml` contract, the `supervisor` actor maps to this
Coordinator profile. Specialist execution maps to Operator, code execution
maps to Explorer, and decisions remain with the user.

## Start with the records

1. Get the Pipeline ID or bounded topic from the request.
2. Use `horology-document-graph` to search relevant documents, related documents, `get_item_history` and `list_runs` as appropriate. Distinguish graph history from live workflow state: the graph may lag Sheets and Drive.
3. Load `horology-composio-reader` when current Pipeline, Locations, register, Drive or Docs state affects the answer or delegation. Read only the bounded records needed for the task.
4. Identify the relevant specialist skill. Answer a bounded status question directly, or delegate a task with its live status, evidence, configured locations, acceptance criteria and approval gate.
5. State the finding, evidence links, what remains uncertain, and the next useful action.

## Google and execution boundary

Coordinator's Composio session is intentionally read-only. It may inspect the
live Pipeline Sheet, Locations, registers, Drive metadata and linked Docs to
plan and route work. It must not select or claim rows, change stages or
statuses, append records, edit documents, move files or perform any other
Google write.

Delegate authorised non-code execution and Google writes to Operator. Delegate
code work to Explorer. Do not claim a Pipeline run, saved deliverable or live
record change until the worker provides evidence and Coordinator verifies the
result. A graph `write_document` saves an agent document in Neon; it does not
perform a Sheet or Drive action.

## Kanban profile routing

Use Hermes Kanban for every cross-profile execution task. Create a bounded task
and explicitly assign it to one allowed profile:

- `operator` for non-code research, browser work, documents, reports and
  authorised Google Workspace operations;
- `explorer` for code execution, repository changes, tests and dependency
  work in its isolated Modal environment.

Include a self-contained goal, the relevant live evidence and links,
constraints, the applicable Horology skill, acceptance criteria, expected
output and any approval gates. Never place credentials in a task. Do not mark a
user approval gate as approved unless the user approved it.

Call `kanban_create` with a short `title`, the explicit `assignee`, and the full
task specification in `body`. Use `skills` only for skill names installed on
that assignee. Use `parents` when a task must wait for earlier work; do not rely
on prose to express a dependency.

Kanban is required because its dispatcher launches the assigned worker as the
full profile, with that profile's configuration, credentials, toolsets and
skills. Do not use `delegate_task` for Operator or Explorer work: delegated
children inherit Coordinator's available toolsets and may not have the tools
required by the worker profile. Do not claim that a profile is working unless a
real Kanban task and run exist. Review the worker's result and evidence before
relying on it or reporting completion.

## Status questions

Use `list_runs` for recent runs and `get_item_history` for one item. Follow links to original documents where available. Group the answer into running, finished, failed, and awaiting user action. Do not present a claimed run as completed, or an indexed document as current without checking its date and source.

## Decisions

The user chooses among proposals. Hermes may explain options or prepare a recommendation. Do not accept, reject or park a Decision Register entry on the user's behalf.
