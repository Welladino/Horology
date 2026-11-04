# Stage 4 items end Completed

## Context

Investigation-route items that reached Stage 4 stayed **Awaiting decision** and could not be accepted on the decision page (HOR-14, Pipeline item 67). Supervisor step 9 and `horology-synthesis-artifacts` moved the item to Awaiting decision / Stage 4 / Specialist deliverable, but nothing proposed a Stage 4 decision. Current decision ID still named the accepted Stage 2 Investigation proposal decision, so `decide()` in `Rules.js` refused it ("is for Investigation proposal but the item is reviewing Specialist deliverable"). Items 45 and 53 were set to Completed by hand. The implementation route was not affected: it already ends Completed at Stage 3.

The founder answered the Implementation question (Decision 15) on 03/11/2026 with Option C.

## Decision

- **Completed at Stage 4 on save.** `synthesize-stage-3` moves the item from Researching / Stage 3 to **Completed** / Stage 4 / Review stage Specialist deliverable / No action.
- **A Specialist deliverable decision is still recorded.** In the same run the supervisor reserves a Decision ID, proposes a decision (Options for accept, rework and park, one Recommended) and makes it the Current decision ID. It stays **proposed**; agents never record acceptance.
- **The review stays open on a Completed item.** A new `open_review` list in `workflow.yaml` (`OPEN_REVIEW` in `Rules.js`) says where a current proposed decision can be decided: Awaiting decision, or Completed at Stage 4 with Review stage Specialist deliverable. Accepting there changes nothing (`accept-stage-3`, Completed → Completed). Rework, park or reject reopen the item. `rework`, `decide-park` and `decide-reject` now also start from Completed. This closes the gap found in step 1: `revise` needs a decided decision, so it could not have reopened an item from a proposed one.
- **Old items are left as they are.** A Completed item whose current decision is for another Review stage (items 45 and 53) has no open review. The decision script skips it without reporting an error.

## What changed

- `workflow.yaml`: `synthesize-stage-3`, `accept-stage-3`, `rework`, `decide-park` and `decide-reject`; new `open_review`; the meanings of Completed and Stage 4.
- `google_appscript/pipeline-decisions`:
  - `Rules.js`: `OPEN_REVIEW`, `reviewOpen()`, and `decide()` skipping an already applied (no-change) outcome.
  - `Apply.js`: reports that no-change outcome as applied for the web page.
  - `WebApp.js`: uses `reviewOpen()` for the inbox, the reading pane and saving.
  - `Review.html`: shows a "Keep completed" label and a one-line hint for a Completed item.
  - Tests for all of the above.
- Skills: supervisor step 9 and its boundaries, `horology-synthesis-artifacts`, the capture-triage records reference, and the digest checks. A proposed Stage 4 decision is not counted as a blocked item, and a Completed Stage 4 item without one is flagged as a missing record.
- Docs: the workflow page and its diagram, Apps Script, workflow operations, and How Horology works.
- Codex plugin versions: horology-workflows 0.6.10 (PR 9 for item 63 takes 0.6.9) and horology-specialists 0.2.9.
- Unchanged: ClickUp sync. Completed is comment-only, so the task status is left to the founder as before. The document-graph history checks read `workflow.yaml`, so Researching → Completed is now an expected move once the service is redeployed.

## Verification

- `.venv/bin/python -m pytest tests/unit -q`, and `npm test` in `google_appscript/pipeline-decisions`.
- Not verified live: no `clasp push`, skill upload or document-graph redeploy was made.

## Founder steps

1. Merge item 65's branch first, then this one, and check `Review.html` for conflicts.
2. In `google_appscript/pipeline-decisions`, run `npm test`, then `npm run clasp:push`, and deploy a new version of the existing web-app deployment.
3. Rebuild and upload the changed skills ([runbook](../../runbook/subscription-agents/claude_skills.md)): `python3 scripts/ops/claude/build_skill_zips.py horology-supervisor horology-synthesis-artifacts horology-capture-triage horology-digest`. Rebuild the Codex plugins as usual.
4. Redeploy the document-graph service so its image carries the new `workflow.yaml`.

## Follow-ups

- Revising item 45's or 53's current decision would apply an Investigation proposal outcome (back to Approved, Stage 3). Use a new item rather than revise if either needs reopening.
- The pipeline-decisions time trigger was removed earlier. A decision written through the Sheets API (by an agent) is applied only when someone runs `applyDecisions`. Decision 15 waited more than 10 minutes for this reason.
