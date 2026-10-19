---
name: horology-watcher-setup
description: Set up, change, pause or remove a watcher, a scheduled agent that checks something on a regular cadence (competitor launches, campaigns, prices, mentions, releases) and reports back. Offers choices, writes a self-contained prompt that points the run at the right Agent reference and Agent output folders, creates the schedule on Claude or Codex after the founder agrees, and records it on the Watchers tab of the Agent Register. Use when the founder asks to watch, monitor or track something regularly.
---

# Watcher setup

## When to use

"Watch what new products our competitors launch every week", "track their ad campaigns monthly", "pause the pricing watcher", "change the launch watcher to Mondays". Not for one-off research (that's a Pipeline item for `horology-research`) or for running Pipeline items on a timer.

A watcher is a row on the **Watchers** tab plus a scheduled task on Claude or Codex that runs the row's **Prompt**. Each run reads what it's told to, checks only what's new since its last report, writes a dated report, and records it. It reports; it never acts on what it finds.

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md). A watcher reads the domain's **Agent reference** folders when its job needs them, and saves to an **Agent output** folder.
- The Agent Register is linked on the Pipeline's **Registers** tab ([Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit)). Its **Watchers** tab has: ID, Name, Domain, Entity, What to watch, Agent reference, Report folder, Connectors, Schedule, Timezone, Platform, Status, Prompt, Schedule reference, Last run, Last report. Map columns by header name.
- The prompt is built from [the watcher prompt](references/prompt.md).
- Scheduling:
  - **Claude:** a routine, in Anthropic's cloud, at most hourly. Create it with `/schedule` in a Claude Code session, the Routines page at claude.ai/code/routines, or the desktop app's Routines.
  - **Codex:** a standalone scheduled task, created by asking Codex in a chat, or in the Scheduled view of the ChatGPT desktop app or web. A task created on the web runs without the computer on; a project-scoped one needs it on.

## Ask with choices

Ask one question at a time, with short numbered choices built from the sheets (domains, entities, folders) and the likely answer first:

1. **Set up a new watcher**, change one, pause or resume one, or remove one.
2. **What to watch**, in one or two sentences: the question each run answers. Offer examples from the domain: new product launches, ad and email campaigns, price changes, press and social mentions, app or product releases.
3. **Domain and entity**, from the Domains tab.
4. **What it reads:** the domain's Agent reference folders that matter (a competitor list, brand notes), or none. If the targets aren't written down anywhere, offer to put the list in the prompt instead.
5. **Report folder:** an Agent output folder for the domain. If none fits, offer `horology-workspace-setup` to add one.
6. **Connectors it may use:** Google Drive, Docs and Sheets (always, to read and save), the Horology gateway for web search and page reading, and any others the job needs. Fewer is safer: a scheduled run uses every tool of a connector it's given without asking.
7. **Schedule and timezone:** daily, weekdays, weekly on a day, monthly; a time a few minutes past the hour (e.g. 09:07) so it starts on time.
8. **Platform:** Claude (routine) or Codex (scheduled task), and for Claude the model to use.

## Workflow

1. Read the Watchers tab, the Domains and Locations tabs, and the chosen folders' links.
2. Gather the choices above.
3. **Show the plan before doing anything:** the Watchers row, the full prompt (from [the watcher prompt](references/prompt.md), filled in), the schedule and the connectors. Ask: set it up as shown, change something, or cancel.
4. After a yes:
   1. Add the row with Status **Draft** and the next ID, so the prompt can name its own row.
   2. Create the scheduled task with the prompt, the schedule, the connectors and, on Claude, the model. In Claude Code use `/schedule`; in Codex ask to create a standalone scheduled task. If this session can't create it, give the founder the prompt and the exact steps, and leave the row as Draft.
   3. Write the task's link or ID to **Schedule reference** and set Status **Active**.
5. Offer a first run now (Run now on the routine, or run the Codex task once) so the founder sees a report straight away.
6. For a change, pause or removal: show the row and what changes, then update the task the same way and the row to match (Paused keeps the task but turns it off; removal deletes the task and sets Status Paused with a note, keeping the row as history).

## Decision and permission boundaries

- Create, change or delete a scheduled task only after the founder approves the plan shown in this conversation.
- A watcher reports. Its prompt must not create Pipeline items, change other rows, send messages or publish anything; if a finding needs action, the report says so and the founder decides.
- Don't create folders; use `horology-workspace-setup` for a missing one.

## Output requirements

- The watcher's row, its prompt, the schedule and where it runs, the Schedule reference, and whether a first run was started.
- Reminders, as they apply: check the first report; keep the Agent reference material it reads current; remove connectors the task doesn't need on the routine or task page.

## Verification before finishing

- Read back the Watchers row: Status matches the task (Active only when the task exists and is on), Schedule reference opens it, Report folder is an Agent output folder.
- The prompt in the row is the one the task runs.
