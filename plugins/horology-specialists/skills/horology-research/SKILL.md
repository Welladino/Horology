---
name: horology-research
description: Investigate a selected Welladino Pipeline question, save evidence and recommendations to Drive, and link the research to Pipeline and the central registers. Use for scoped business or technical research, not implementation.
---

# Research

## When to use

Investigate a selected Pipeline question and record evidence, options, and recommendations. Keep implementation and recurring schedules separate until this workflow is tested.

## Required context and locations

- Read the current [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit) and [Agent Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit) for rules and verified destinations.
- Read the [Document Presentation Guide](https://docs.google.com/document/d/1D2N9VJRCmBFJ4T9cUGH47zQUVqk99sjavpbbwYIYY8I/edit) before creating or filling documents, and [linking rules](references/linking.md) when saving outputs.
- Identify the selected Pipeline item by its permanent numeric ID; historical EPIC-NEWS references belong to External ID. Resolve a bounded question, expected output, and stopping point from the request; clarify material missing scope before dependent work.
- These rules are portable; tool availability and authentication are platform-specific.

## Workflow

Edit Pipeline Master only; filter its table to see one domain. Resolve records by permanent Pipeline ID and map fields by live headers.

1. Reuse existing evidence before creating another document. For Article Aggregator code claims, follow its AGENTS.md, inspect the graph and architecture map first, then verify relevant source at the current revision. For external technical claims, use primary sources and verify changing facts.
2. Copy the native Research template into the verified domain/entity Research destination before filling it. Preserve metadata and section roles; use the platform's document-editing safeguards and native link controls where supported.
3. Keep evidence, alternatives, recommendations, and uncertainties distinct. Distinguish source behavior, deployed behavior, and assumptions; explain material access gaps. Stop when the scoped question is answered or remaining gaps require user input.
4. Read live sheet headers and map fields by name. Upsert the Document Index by Drive file ID, preserve existing document IDs, and associate the document through Document Index and update Pipeline's next step. Mark **Awaiting decision** when the selected investigation is complete.
5. If the requested workflow includes a decision, draft a **proposed** record in Decision Register Master with evidence and a review trigger. Copy and link a **Draft Plan** when useful to make the recommendation reviewable. Create a Direction document only when the choice concerns purpose, audience, positioning, or priorities.

## Decision and permission boundaries

ID is permanent and unique across the whole Pipeline. Allocate the next unused numeric ID; never renumber after sorting or reuse a removed ID. External ID is optional and holds historical EPIC-NEWS or other source identifiers. Entity is only for named Newsletter or Ecommerce businesses; leave it empty for Article Aggregator, Welladino and Horology.

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

- Read back documents and affected records; verify identities, backlinks, and preservation of unrelated cells.
- Check native headings, lists, table headers, readable spacing, and removal of leftover placeholders. When layout matters, inspect a rendered preview or disclose that it was unavailable.
- Check visual labels, captions, source links, and readability at normal document width. Verify chart data and diagram source match the inserted visual.
- Inspect destinations after ambiguous write failures before retrying.
- Confirm recommendations remain proposed until the founder explicitly chooses, and distinguish saved work from pending writes.
