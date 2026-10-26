---
name: horology-coordinator
description: Orient the user on Horology Pipeline work from the document graph, identify the right specialist skill for a bounded question, and report what Hermes can do with its currently connected tools. Use for Pipeline status and task-routing questions in Hermes.
---

# Horology coordinator

This skill runs in Hermes's Coordinator profile. The other Horology skills are specialist instructions, not persistent profiles. Do not use the retired kanban/persona dispatch system.

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

## Status questions

Use `list_runs` for recent runs and `get_item_history` for one item. Follow links to original documents where available. Group the answer into running, finished, failed, and awaiting user action. Do not present a claimed run as completed, or an indexed document as current without checking its date and source.

## Decisions

The user chooses among proposals. Hermes may explain options or prepare a recommendation. Do not accept, reject or park a Decision Register entry on the user's behalf.
