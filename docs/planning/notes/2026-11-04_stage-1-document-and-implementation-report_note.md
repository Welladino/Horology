# Stage 1 document on every route, Implementation report and Stage 4 page

## Context

The implementation route (Feature, Enhancement, Refactor, Fix) wrote only Steps rows and ended Completed at Stage 3. A plan document was optional, so an Implementation question had nothing to link (item 68 made Research Links Drive-only), and nothing told the founder what was done: `finish_run` notes and `get_item_history` hold short self-reports in Neon that only an agent can read. Item 69 was split from HOR-9 for this; the founder decided the approach on 04/11/2026 (Pipeline 69, Summary / Why).

## Decision

1. **Every route starts with a Stage 1 specialist document in Drive plus Steps rows.** The document uses the Research, Direction, Plan or Technical Assessment template. On the implementation route it is usually a Plan (a technical assessment when options must be compared first), and the run carries on to Stage 3 without a review unless an Implementation question comes up; that question's Research Links name the Stage 1 document. On the investigation route a Stage 1 run that finds no open Steps rows writes the steps of its own investigation (an interpretation made in this run; the founder's wording was "plus Steps rows").
2. **Implementation report at Stage 3.** A new **Implementation report — Template** in the Horology templates folder, listed on the Templates tab: summary, what changed and why, commits and pull request, tests and checks, changes from the plan, and what's left for the founder. The report is saved in the same Agent output folder as the item's Stage 1 document unless a folder's Purpose names implementation reports, so no new folder is needed.
3. **Stage 4 page, then Completed.** `horology-synthesis-artifacts` makes a page from the report in the same run. As for the investigation route since item 67, the run proposes a Specialist deliverable decision, makes it the Current decision ID and sets **Completed** / Stage 4 / Specialist deliverable (`complete-implementation`). The Docs are the record; the pages do not reach the document graph.
4. **Graph Inclusion stays the founder's.** A rule in `workflow.yaml`: agents add Document Index rows with it FALSE and never set it TRUE or change it.

## What changed

- `workflow.yaml` version 4: implementation route stages Stage 1, Stage 3, Stage 4; `complete-implementation` ends Completed / Stage 4 / Specialist deliverable (actors supervisor and synthesis); Stage meanings; `raise-implementation-question` names the Stage 1 document; Steps written by a Stage 1 run on either route; the Graph Inclusion rule. Completed still allows Stage 3 for items finished before 04/11/2026.
- `pipeline-decisions`: no rule change was needed. `OPEN_REVIEW` already covers Completed / Stage 4 / Specialist deliverable, and rework on that decision returns the item to Stage 3, where `start-implementation` picks it up. `Rules.js` comment, `WebApp.js` passes `itemType`, and `Review.html` adds "Rework sends the implementation back to Stage 3" for a Completed implementation item. New tests for accept, rework (Ready, or No action for Manual) and park.
- Skills: supervisor (route summary, item-mode Stage 1 steps and document, Implementation route steps 1, 3–6, boundaries, output), its routing and runs references, planner, technical assessment, synthesis artifacts, the capture-triage records reference and the digest checks (missing report, page or Stage 1 document; Stage 4 now right for a finished implementation).
- Docs: the workflow page (routes table, implementation diagram, moves table, stages), workspace records, Apps Script, workflow operations and How Horology works.
- Codex plugin versions: horology-workflows 0.6.12 and horology-specialists 0.2.12.
- Live: the template Doc and its Templates tab row.

## Verification

- `PYTHONPATH=$PWD/document-graph-core:$PWD/mcp-servers/document-graph .venv/bin/python -m pytest tests/unit -q` and `npm test` in `google_appscript/pipeline-decisions`.
- Not verified live: no `clasp push`, skill upload or document-graph redeploy was made.

## Founder steps

1. Merge the branch.
2. In `google_appscript/pipeline-decisions`: `npm test`, `npm run clasp:push`, then deploy a new version of the existing web-app deployment.
3. Rebuild and upload the changed skills: `python3 scripts/ops/claude/build_skill_zips.py horology-supervisor horology-planner horology-capture-triage horology-digest horology-synthesis-artifacts horology-technical-assessment`; rebuild the Codex plugins as usual.
4. Redeploy the document-graph service so its `workflow.yaml` copy marks the new Stage 4 move as expected.
5. Optional: copy the new template into the Starter Pack templates folder for new workspaces.

## Follow-ups

- The watcher prompt and the digest already add rows with Graph Inclusion FALSE, which the new rule allows.
- Stage 4 pages (Cloudflare or Drive HTML) still never reach the document graph; the Docs do when the founder includes them.
