---
name: horology-capture-triage
description: Capture and triage retained ideas, parked proposals, and research requests in Welladino's shared Pipeline across business domains. Use when the user asks to record, transfer, or assess future work.
---

# Capture and triage

## When to use

Capture, transfer, or triage thoughts the user asks to retain across Welladino's domains. Do not turn all brainstorming into backlog entries.

## Required context and locations

- Read [domains, folders and templates](references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Read [record fields](references/records.md) when writing a row. Configure connectors separately for each platform.
- Pipeline owns proposals; Drive owns supporting documents; optional ClickUp tasks are a planning notebook. The ClickUp updater sends status and milestone comments to confirmed task links but never imports ClickUp changes. Repo Markdown is temporary technical capture, not a maintained mirror.
- Resolve domain and entity from the conversation and existing records, using only the values in the Domains tab.

## Workflow

Edit Pipeline Master only; filter its table to see one domain. Resolve records by permanent Pipeline ID and map fields by live headers.

1. Read Pipeline Master and live headers; map fields by name because columns may be reordered.
2. Match existing records by permanent Pipeline ID, source URL, and meaning. Update an existing item rather than duplicate it. ClickUp task URLs uniquely identify tasks even when title prefixes repeat.
3. Preserve historical EPIC-NEWS references in optional External ID. For new items, prefer the Add Pipeline item form; otherwise scan Master and use the next unused numeric Pipeline ID across all domains, as the only capture writer. Never renumber existing IDs.
4. Write a concise title, reason, next question, and supporting links. Use **Inbox** for newly captured work, **Parked** for explicitly deferred work with a revisit trigger, and **Researching** for a selected, authorized investigation.
5. Edit only relevant cells. Find the row by its ID immediately before every update, never by row position; other runs may add or move rows at any time.

## Decision and permission boundaries

ID is permanent and unique across the whole Pipeline. New Pipeline IDs come from the Add Pipeline item form, which allocates them under a lock; when capturing directly in Master, take the next unused numeric Pipeline ID as the only capture writer and re-read Master just before saving. Never renumber after sorting or reuse a removed ID. Decision and Document IDs always come from `reserve_id` ([records](references/records.md)). External ID is optional and holds historical EPIC-NEWS or other source identifiers. Domain and Entity come from the Domains tab: set Entity only when the domain lists entities.

Agent status is No action, Plan or Ready; Agent type is Claude Code, Codex, Manual or Unassigned; Run location is Local or Cloud (blank means Local). Default new captures to No action and Unassigned unless the user selects otherwise. Ready selects the stated Next step / Research question but does not launch an automatic run. A user request or authorised schedule starts work; selection never implies acceptance of a recommendation or permission for unrelated implementation.


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
