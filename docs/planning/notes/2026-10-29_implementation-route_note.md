# Implementation route and In progress status (HOR-12, item 49)

## Context

Every run set Status to Researching, whatever the work, so implementation items (43, 47 and 50) went through the investigation route and ended at Awaiting decision / Investigation proposal or needed hand-edited statuses. Decided by the founder on 29/10/2026 as direct implementation; no investigation.

## Decision

- **Type chooses the route** (`routes` in `workflow.yaml`, version 3). Idea, Research, Direction and Plan keep the investigation route unchanged. Feature, Enhancement, Refactor and a new Type **Fix** take the implementation route.
- **Implementation route:** Stage 1 is the implementation plan, written by the run as Steps rows; the run then moves the item to Stage 3 itself (`plan-implementation`) and implements it in the same run. Status is **In progress** throughout (`start-implementation`). With no founder decision needed it finishes **Completed** at Stage 3 (`complete-implementation`). There is no Stage 2 or Stage 4.
- **Implementation question:** a run that needs a founder choice commits its work so far, drafts a proposed decision with Options rows and stops at Awaiting decision, Stage 3, Review stage **Implementation question** (`raise-implementation-question`). Accepting it on the decision page (**Answer and resume Stage 3**) sets In progress, Stage 3 and Ready for its platform (`resume-implementation`); rework, park and reject work as for other reviews, at Stage 3.
- **Re-selection:** an implementation item left In progress by a failed or stopped run can be made Ready again (`select` now allows In progress). Revising is still refused while an item is In progress; revising a parked Implementation question to accepted resumes the item.
- **ClickUp:** `STATUS_MAP` maps In progress to `in progress`, ClickUp's default in-progress status name. The list's statuses could not be read (ClickUp MCP daily limit), so this is not confirmed against the live list.

## What changed

- `workflow.yaml`: Type field and routes; Status In progress; Review stage Implementation question; five new moves; Completed allowed at Stage 3; park/reject at Stage 3; run-failed from In progress; the founder rule on implementation.
- `pipeline-decisions`: `Rules.js` outcomes for Implementation question; `ItemRules.js` adds Fix, `IMPLEMENTATION_TYPES`, `itemRoute` and `readyStatuses`; `WebItems.js` uses them for the Ready rule; `Review.html` offers Ready from In progress for implementation items, labels the accept outcome of an Implementation question and tones the new values.
- `clickup-sync`: In progress in `STATUS_MAP`.
- Skills: supervisor (route by Type, Implementation route section), routing, runs, planner, capture-triage (Type guidance, records), digest health checks (stalled implementation, wrong route, unfinished steps), technical assessment (when it applies now).
- Live Pipeline Master table: Status dropdown gained In progress and Type gained Fix (additive; no other column changed).
- Docs: workflow (routes, a second lifecycle diagram, move table), workspace records, Apps Script, How Horology works and workflow operations runbooks.

## Verification

- `.venv/bin/python -m pytest tests/unit -q`: 465 passed, including new workflow tests for the routes, the implementation moves, an unchanged investigation route and the Type list in `ItemRules.js`.
- `npm test` in `google_appscript/pipeline-decisions` (decisions, folders, shared UI check) and `google_appscript/clickup-sync` (28 tests): pass. New cases cover answering, reworking, parking and rejecting an Implementation question, no decision applied while In progress, Fix routing and re-selecting an In progress item.
- Not verified live: no `clasp push`, deployment or skill upload was made.

## Founder steps (not done by the run)

1. **Review stage dropdowns (needed before the first Implementation question):** add `Implementation question` to the Review stage dropdown in Pipeline Master and in Decision Register Master (Data → Data validation, or the table column's dropdown settings). The run was told not to touch other columns, so these were left.
2. **ClickUp:** confirm the linked lists have an `in progress` status, or change the value in `google_appscript/clickup-sync/src/Config.js`.
3. **Apps Scripts:** in `google_appscript/pipeline-decisions`, `npm run clasp:push`, then deploy the web page as a new version of the existing deployment ([runbook](../../runbook/subscription-agents/clasp.md#deploy-the-web-page-after-a-change)). In `google_appscript/clickup-sync`, `npx clasp push`.
4. **Skills:** `python3 scripts/ops/claude/build_skill_zips.py horology-supervisor horology-planner horology-capture-triage horology-digest horology-technical-assessment` and upload the zips on claude.ai ([runbook](../../runbook/subscription-agents/claude_skills.md)); rebuild the Codex plugins as usual.
5. **Document graph:** redeploy the document-graph service so its image carries the new `workflow.yaml`; until then `get_item_history` marks the new moves `expected: false`.
