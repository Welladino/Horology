---
name: horology-planner
description: Scope or split Pipeline items set to Agent status Plan (not marketing or content plans) — rewrite Next step as a bounded question, or break it into numbered steps there — then set the item back to No action for the founder to review. Runs on a schedule, when the supervisor hands it an item to scope, or when this skill is named. Only touches Plan rows.
---

# Planner

## When to use

A scheduled run, or when the founder asks to "plan the Plan items" or "plan item 42". The planner prepares items for a run; it never runs them, and only acts on rows with Agent status **Plan**.

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Pipeline field rules are in the capture-triage skill's [records reference](../horology-capture-triage/references/records.md); claiming, finishing and the steps format in the supervisor skill's [runs reference](../horology-supervisor/references/runs.md). Map columns by header name.
- Know the specialists: the installed specialist `horology-*` skills (research, technical assessment, security review, GTM, marketing strategy, content planner) and their descriptions.
- The document-graph connector is required for claims; if it isn't available, stop and say so. Use the `horology-document-graph` skill to see what's already known.

## Workflow

For each Pipeline row with Agent status Plan (or the one item you were given, if it is Plan):

1. Claim it with `claim_item`, kind `plan`, so two planners don't work on it at once. Use the Agent type of the platform you're on and the row's Run location. Skip it if another run holds it.
2. Read the row (Title, Domain, Type, Summary / Why, Next step / Research question, target), its current decision and rework instructions, and `get_item_history` for earlier runs and plans.
3. Search the document graph for what's already researched or decided on the subject.
4. Decide what the item needs:
   - **A sharper question:** the item is one piece of work but its question is vague or too broad.
   - **A split:** it needs several distinct pieces of work, often for different specialists or in an order.
   - **Nothing more:** it's already well scoped, or the graph already answers it. Say so in the `finish_run` notes.
5. For a sharper question, rewrite Next step / Research question as one bounded question with what "answered" looks like. Keep the old wording for the `finish_run` notes.
6. For a split, rewrite Next step / Research question as a numbered list: one bounded question or task per line, in order, ending with the suggested specialist in brackets where one clearly fits. Keep the old wording for the notes. Usually 2–5 steps; if it needs more, it should probably be separate Pipeline items, so say that instead.
7. Set Planner output to **Yes** (unless nothing changed), Agent status to **No action**, and Updated to today. Call `finish_run` as done, with the old wording and a one-line reason in notes.

## Decision and permission boundaries

- Only Plan rows. Never touch other rows, and never set an item to Ready: the founder reviews the plan and marks it Ready.
- Don't create new Pipeline rows. Splits go in Next step.
- Don't change Agent type, Run location, Status, Stage or decisions.
- Don't start any specialist work.

## Output requirements

- Per item: what changed (new question, or the list of steps with suggested specialists), or why nothing was needed.
- A short summary: items planned, items skipped (claimed, not Plan) and why.

## Verification before finishing

- Read back the Pipeline cells you wrote; confirm unrelated cells were preserved.
- Confirm every planned item is back to No action with Planner output Yes, and its run is finished.
