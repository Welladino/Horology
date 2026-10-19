---
name: horology-template
description: Create a new document template for the agents, or revise an existing one, as a Google Doc in the workspace's templates folder, then ask whether to add or update its row on the Pipeline's Templates tab. Use when the founder wants a kind of document (a brief, a report, a checklist, a review) that agents should produce in a consistent shape.
---

# Template

## When to use

The founder asks for a new template ("make a template for competitor briefs") or a change to one ("add a risks section to the Plan template"). Not for filling a template for a Pipeline item (the specialists do that) or for folders (use `horology-workspace-setup`).

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md), and follow the [presentation rules](../horology-digest/references/presentation.md) for the template's own structure.
- The templates folder is the Agent reference folder for templates in the Pipeline's Locations tab (its Name or Purpose says templates). If there is none, or several, ask which to use; use `horology-workspace-setup` to add one.
- Read the Templates tab, and open the one or two existing templates closest to the request, to match their metadata block, section style and guidance.

## Ask with choices

Ask one question at a time, offering short numbered choices built from what you've read, with the likely answer first and "something else" last:

1. What the document is for, and which decision or work it supports.
2. Who reads it, and which specialists would produce it (research, GTM, marketing, content, technical assessment, security review, or a new use).
3. The sections: propose a list based on the purpose and the closest existing template; the founder keeps, drops, renames or adds sections.
4. For a revision: what changes, and whether to edit the template itself or start a new version alongside it.

## Workflow

1. Gather the answers above.
2. **Show the outline before writing:** the title (`<Name> — Template`), the metadata block, and each section heading with one line on what goes in it. Ask: create it, change something, or cancel.
3. After a yes, create the Google Doc in the templates folder, or edit the existing template:
   - Native headings, lists and tables, per the presentation rules.
   - A metadata block at the top like the existing templates (domain, entity, Pipeline ID, status, related decision, date).
   - Guidance in each section as short bracketed placeholders the filler replaces, e.g. `[Who the customer is, in one paragraph]`.
   - An example table only where the section is a comparison or a list of milestones.
4. **Ask about the Templates tab:**
   1. Add a row (new template)
   2. Update its row (revised template, if its Use changed)
   3. Not now

   For a row, propose the Template name, the Location (the Doc's link) and a one-line Use that tells a specialist when to pick it, then write it after a yes.
5. If a specialist should always use this template rather than choosing it by its Use line, tell the founder: that's a change to the specialist's skill, not to the sheet.

## Decision and permission boundaries

- Templates are originals: never fill one with real content, and edit an existing one only when the founder asked for that template to change.
- Create only the one Doc agreed in the outline. Don't move, rename or delete other files.
- Don't add the template to the Document Index or the document graph.

## Output requirements

- The template's link, its outline, and whether its Templates row was added, updated or left for later.

## Verification before finishing

- Re-open the Doc: headings are real headings, placeholders are clear, no leftover instructions to you.
- If a Templates row was written, read it back and check the link opens the new Doc.
