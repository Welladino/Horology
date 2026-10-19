---
name: horology-watcher-setup
description: Set up, change, pause or remove a scheduled agent — a watcher that checks something on a regular cadence (competitor launches, campaigns, prices, mentions, releases) and reports back, or a schedule for the digest, planner, a periodic security review or the document-graph sync. Offers choices, writes a self-contained prompt, creates the schedule on Claude or Codex after the founder agrees, and records it on the Watchers tab of the Agent Register. Use when the founder asks to watch, monitor or track something regularly, or to run one of those agents on a schedule.
---

# Watcher setup

## When to use

"Watch what new products our competitors launch every week", "track their ad campaigns monthly", "pause the pricing watcher", "change the launch watcher to Mondays". Not for one-off research (that's a Pipeline item for `horology-research`) or for running Pipeline items on a timer.

Every scheduled agent is a row on the **Watchers** tab plus a scheduled task on Claude or Codex that runs the row's **Prompt**. The row's **Type** says what kind it is:

| Type | What each run does | Prompt |
|---|---|---|
| **Watcher** | Checks something, reports only what's new since its last report, records the report. Never acts on what it finds. | Built from [the watcher prompt](references/prompt.md) |
| **Digest** | Writes the daily report card | "Use the horology-digest skill to write today's digest." |
| **Planner** | Scopes or splits the Pipeline rows set to Plan | "Use the horology-planner skill to plan the Pipeline items set to Plan." |
| **Security review** | A read-only review of one named repository, compared with the last review | "Use the horology-security-review skill for a periodic security review of <repository>, branch <branch>; save it as the skill describes." |
| **Graph sync** | Starts the Document Index sync into the document graph | "Use the horology-document-graph skill to start the Document Index sync with sync_graph, then report what it started." |

Running the supervisor on Ready items is deliberately not a type: Pipeline work starts only when the founder asks.

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md). A watcher reads the domain's **Agent reference** folders when its job needs them, and saves to an **Agent output** folder.
- The Agent Register is linked on the Pipeline's **Registers** tab ([Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit)). Its **Watchers** tab has: ID, Name, Type, Domain, Entity, What to watch, Agent reference, Report folder, Connectors, Schedule, Timezone, Platform, Status, Prompt, Schedule reference. Map columns by header name. For types other than Watcher, What to watch, Agent reference and Report folder may stay blank; the skill the prompt names knows where to read and save.
- The prompt is built from [the watcher prompt](references/prompt.md).
- Scheduling:
  - **Claude:** a routine, in Anthropic's cloud, at most hourly. Create it with `/schedule` in a Claude Code session, the Routines page at claude.ai/code/routines, or the desktop app's Routines.
  - **Codex:** a standalone scheduled task, created by asking Codex in a chat, or in the Scheduled view of the ChatGPT desktop app or web. A task created on the web runs without the computer on; a project-scoped one needs it on.

## Ask with choices

Ask one question at a time, with short numbered choices built from the sheets (domains, entities, folders) and the likely answer first:

1. **Set up a new scheduled agent**, change one, pause or resume one, or remove one.
2. **Type:** Watcher, Digest, Planner, Security review or Graph sync. For anything but a watcher, skip to connectors (7), schedule (8) and platform (9); a security review also needs the repository and branch.
3. **What to watch** (watchers), in one or two sentences: the question each run answers. Offer examples from the domain: new product launches, ad and email campaigns, price changes, press and social mentions, app or product releases.
4. **Domain and entity**, from the Domains tab.
5. **What it reads:** the domain's Agent reference folders that matter (a competitor list, brand notes), or none. If the targets aren't written down anywhere, offer to put the list in the prompt instead.
6. **Report folder:** an Agent output folder for the domain. If none fits, offer `horology-workspace-setup` to add one.
7. **Connectors it may use:** Google Drive, Docs and Sheets (always, to read and save), the Horology gateway for web search and page reading, the document-graph connector for the digest, planner and graph sync, GitHub for a security review, and any others the job needs. Fewer is safer: a scheduled run uses every tool of a connector it's given without asking.
8. **Schedule and timezone:** daily, weekdays, weekly on a day, monthly; a time a few minutes past the hour (e.g. 09:07) so it starts on time.
9. **Platform:** Claude (routine) or Codex (scheduled task), and for Claude the model to use.

## Workflow

1. Read the Watchers tab, the Domains and Locations tabs, and the chosen folders' links.
2. Gather the choices above.
3. **Show the plan before doing anything:** the Watchers row, the full prompt (a watcher's from [the watcher prompt](references/prompt.md), filled in; another type's from the table above), the schedule and the connectors. Ask: set it up as shown, change something, or cancel.
4. After a yes:
   1. Add the row with Status **Draft** and the next ID, so the prompt can name its own row.
   2. Create the scheduled task with the prompt, the schedule, the connectors and, on Claude, the model. In Claude Code use `/schedule`; in Codex ask to create a standalone scheduled task. If this session can't create it, give the founder the prompt and the exact steps, and leave the row as Draft.
   3. Write the task's link or ID to **Schedule reference** and set Status **Active**.
5. Offer a first run now (Run now on the routine, or run the Codex task once) so the founder sees a report straight away.
6. For a change, pause or removal: show the row and what changes, then update the task the same way and the row to match (Paused keeps the task but turns it off; removal deletes the task and sets Status Paused with a note, keeping the row as history).

## Decision and permission boundaries

- Create, change or delete a scheduled task only after the founder approves the plan shown in this conversation.
- A watcher reports. Its prompt must not create Pipeline items, change other rows, send messages or publish anything; if a finding needs action, the report says so and the founder decides. The other types do only what their skill allows.
- Don't schedule the supervisor to run Ready items.
- Don't create folders; use `horology-workspace-setup` for a missing one.

## Output requirements

- The row, its prompt, the schedule and where it runs, the Schedule reference, and whether a first run was started.
- Reminders, as they apply: check the first report; keep the Agent reference material it reads current; remove connectors the task doesn't need on the routine or task page.

## Verification before finishing

- Read back the Watchers row: Status matches the task (Active only when the task exists and is on), Schedule reference opens it, and a watcher's Report folder is an Agent output folder.
- The prompt in the row is the one the task runs.
