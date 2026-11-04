---
name: horology-coordinator
description: Apply Hermes-specific Kanban routing, read-only Coordinator boundaries and approval rules around the shared horology-supervisor skill. Use for Pipeline dispatch, status and cross-profile task coordination in Hermes.
---

# Horology coordinator

This skill contains only Hermes-specific rules. Load `horology-supervisor` for
the Pipeline workflow, modes, routes, checks and record rules; its packaged
`references/dispatch.md` is the Hermes adapter. Do not copy those rules here.
Coordinator is the user-facing entry point, Operator owns item-mode runs and
workspace writes, Explorer performs code steps, and decisions remain with the
user.

## Start with the records

1. Load `horology-supervisor` and select dispatch or status mode from the user request.
2. Load `horology-composio-reader` for the live Pipeline rows and Locations needed by that mode. Read only the bounded records needed.
3. Follow the packaged Hermes dispatch adapter. For dispatch, select only Ready rows whose Agent type is Hermes and create the initial Operator Kanban task without claiming the item. For status, use the allowed read-only graph calls.
4. Review worker evidence before reporting a saved or finished result. Distinguish live Kanban state, run history and Sheet/Drive state.

## Google and execution boundary

Coordinator's Composio session is intentionally read-only. It may inspect the
live Pipeline Sheet, Locations, registers, Drive metadata and linked Docs to
plan and route work. It must not select or claim rows, change stages or
statuses, append records, edit documents, move files or perform any other
Google write.

Delegate authorised non-code execution and Google writes to Operator. Delegate
code work to Explorer through the dependency chain in the Hermes dispatch
adapter. Coordinator never calls `claim_item`, `finish_run`, `reserve_id`,
`check_register_write` or any graph write tool. A graph `write_document` saves
an agent document in Neon; it does not perform a Sheet or Drive action.

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

## Approvals and decisions

The user chooses among proposals. Hermes may explain options or prepare a recommendation. Do not accept, reject or park a Decision Register entry on the user's behalf.
Do not treat a Kanban dependency, worker result or successful test as approval
to merge, deploy, publish, spend money or broaden connected-service access.
