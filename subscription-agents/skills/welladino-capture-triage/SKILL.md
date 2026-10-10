---
name: welladino-capture-triage
description: Capture and triage retained ideas, parked proposals, and research requests in Welladino's shared Pipeline across business domains. Use when the user asks to record, transfer, or assess future work.
---

# Capture and triage

## When to use

Capture, transfer, or triage thoughts the user asks to retain across Welladino's domains. Do not turn all brainstorming into backlog entries.

## Required context and locations

- Read the current [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit) and [Agent Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit) for shared rules and verified destinations.
- Read [record fields](references/records.md) when writing a row. Configure connectors separately for each platform.
- Pipeline owns proposals; Drive owns supporting documents; ClickUp presents Pipeline tasks and review status. Repo Markdown is temporary technical capture, not a maintained mirror.
- Resolve domain and entity from the conversation and existing records. Newsletter and Ecommerce staging folders are not named businesses.

## Workflow

Edit Pipeline Master only; domain tabs are automatic views. Resolve records by permanent Pipeline ID and map fields by live headers.

1. Read Pipeline Master and live headers; map fields by name because columns may be reordered.
2. Match existing records by permanent Pipeline ID, source URL, and meaning. Update an existing item rather than duplicate it. ClickUp task URLs uniquely identify tasks even when title prefixes repeat.
3. Preserve historical EPIC-NEWS references in optional External ID. For new items, scan Master and use the next unused numeric Pipeline ID across all domains; never renumber existing IDs.
4. Write a concise title, reason, next question, and supporting links. Use **Inbox** for newly captured work, **Parked** for explicitly deferred work with a revisit trigger, and **Researching** for a selected, authorized investigation.
5. Edit only relevant cells. Re-read identity immediately before updating after sorting or concurrent changes.

## Decision and permission boundaries

ID is permanent and unique across the whole Pipeline. Allocate the next unused numeric ID; never renumber after sorting or reuse a removed ID. External ID is optional and holds historical EPIC-NEWS or other source identifiers. Entity is only for named Newsletter or Ecommerce businesses; leave it empty for Article Aggregator and Welladino.

Agent status is No action or Ready; Agent type is Manual, Unassigned, ChatGPT, ChatGPT Work, Codex, Claude Code, Claude Cowork, or Horology. Default new captures to No action and Unassigned unless the user selects otherwise. Ready selects the stated Next step / Research question but does not launch an automatic run. A user request or authorised schedule starts work; selection never implies acceptance of a recommendation or permission for unrelated implementation.


- Type Research alone is not permission to start work. Researching requires an investigation selected by the user or an authorized schedule.
- Preserve rejected history unless the user reopens it.
- Transfer useful source details and links before clearing a capture. A destination row alone does not authorize removing source records.
- If access is unavailable, keep unsaved records pending; do not recreate inaccessible ClickUp tasks or claim synchronization.

## Output requirements

- A retained or updated Pipeline item with its identity, concise context, next step, status, and supporting links.
- A brief report of what was captured or changed, including any pending writes or access limitations.

## Verification before finishing

- Read back saved values, identities, and links; confirm unrelated cells were preserved.
- After an ambiguous write failure, inspect the destination before retrying to avoid duplicates.
- Distinguish verified saved changes from pending work in the handoff.
