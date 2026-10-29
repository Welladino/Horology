---
name: horology-research
description: Investigate a selected Pipeline question, save evidence and recommendations to Drive, and link the research to Pipeline and the central registers. Use for scoped business or technical research, not implementation. Usually run by horology-supervisor; use directly only when this skill is named.
---

# Research

## When to use

Investigate a selected Pipeline question and record evidence, options, and recommendations. Keep implementation and recurring schedules separate until this workflow is tested.

## Required context and locations

- Read [domains, folders and templates](references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Follow the [presentation rules](references/presentation.md) when creating or filling documents.
- Read [linking rules](references/linking.md) when saving outputs.
- Identify the selected Pipeline item by its permanent numeric ID; historical EPIC-NEWS references belong to External ID. Resolve a bounded question, expected output, and stopping point from the request; clarify material missing scope before dependent work.
- These rules are portable; tool availability and authentication are platform-specific.

## Workflow

Edit Pipeline Master only; filter its table to see one domain. Resolve records by permanent Pipeline ID and map fields by live headers.

1. Reuse existing evidence before creating another document. Read the domain's relevant Agent reference folders. For code claims, follow the target repository's own instructions (AGENTS.md, CLAUDE.md) and any code graph or architecture map it has, then verify the relevant source at the current revision. For external technical claims, use primary sources and verify changing facts.
2. Copy the Research template from the Templates tab into the Agent output folder that fits before filling it. Preserve metadata and section roles; use the platform's document-editing safeguards and native link controls where supported.
3. Keep evidence, alternatives, recommendations, and uncertainties distinct. Distinguish source behavior, deployed behavior, and assumptions; explain material access gaps. Stop when the scoped question is answered or remaining gaps require user input.
4. Read live sheet headers and map fields by name. Find an existing Document Index row by Drive file ID and keep its document ID; for a new document, reserve the ID with `reserve_id` and check ownership with `check_register_write` before writing, as in the [linking rules](references/linking.md). Associate the document through Document Index and update the Pipeline row, found by its ID, with the next step. Mark **Awaiting decision** when the selected investigation is complete.
5. If the requested workflow includes a decision, reserve its Decision ID with `reserve_id`, check ownership, and draft a **proposed** record in Decision Register Master with evidence and a review trigger. Copy and link a **Draft Plan** when useful to make the recommendation reviewable. Create a Direction document only when the choice concerns purpose, audience, positioning, or priorities.

## Decision and permission boundaries

Pipeline, Decision and Document IDs are permanent: never renumber after sorting or reuse a removed ID. Research never creates Pipeline items; Decision and Document IDs come from `reserve_id`, never from the next unused number in the sheet. External ID is optional and holds historical EPIC-NEWS or other source identifiers. Domain and Entity come from the Domains tab: set Entity only when the domain lists entities.

Agent status is No action, Plan or Ready; Agent type is Claude Code, Codex, Manual or Unassigned; Run location is Local or Cloud (blank means Local). Default new captures to No action and Unassigned unless the user selects otherwise. Ready selects the stated Next step / Research question but does not launch an automatic run. A user request or authorised schedule starts work; selection never implies acceptance of a recommendation or permission for unrelated implementation.


- Research tags alone do not authorize recurring research. A requested research test is not acceptance of its recommendation.
- The founder chooses proceed, revise, further research, park, or reject. Record **accepted** and the actual decision date only after an explicit choice.
- Do not invent scores, observed outcomes, approvals, dates, or commitments. Do not expand a pilot into implementation.
- Research completion alone does not authorize ClickUp execution tasks or graph-synced flags.

## Output requirements

- A scoped research document with evidence, options, recommendation, uncertainties, and sources, associated with Pipeline through Document Index.
- When included in the requested workflow, a proposed decision and linked Draft Plan; preserve their unapproved status.
- Use prose for explanation, native bullets for parallel points, numbered lists for sequences, and tables for meaningful comparisons or milestone details. Give dependencies and milestones separate native subsections; avoid steps or arrow chains buried in paragraphs. Adapt or remove optional template examples.
- When useful, render diagrams as images and retain editable sources; use linked Sheets charts for changing data where supported or clearly labelled snapshots otherwise. Include captions, short explanations, and source links.
- Report findings, the next decision or information needed, and any limitations or unsaved changes plainly.

## Verification before finishing

- Read back documents and affected records by ID; verify identities, backlinks, and preservation of unrelated cells. If `check_register_write` refused a write, report the clash instead of overwriting.
- Check native headings, lists, table headers, readable spacing, and removal of leftover placeholders. When layout matters, inspect a rendered preview or disclose that it was unavailable.
- Confirm the document has no inserted images or charts; comparisons and figures are native tables (see the presentation rules).
- Inspect destinations after ambiguous write failures before retrying.
- Confirm recommendations remain proposed until the founder explicitly chooses, and distinguish saved work from pending writes.
