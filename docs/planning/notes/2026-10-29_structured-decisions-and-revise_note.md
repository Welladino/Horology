# Structured decision options, planned steps and revising decisions (HOR-8 A+B)

## Topic
- structured-decisions-and-revise

## Context
- Decision and Next step cells held long paragraphs. The decision page found options by parsing "Option X" from the Decision text, so Decision 6 ("Proposed (Option B): … Alternatives: A …; C …") showed only Option B.
- A decision already applied could not be changed from the page; the founder had to edit the Pipeline row by hand.
- Pipeline item 43, run R-21. Parts 4–5 of HOR-8 are handled elsewhere (items 44 and 45).

## Decision
- **Options tab** on the Decision Register: one row per option (Decision ID, Code, Summary, Recommended, optional Key figures). The Master Decision cell keeps a one-line summary. Key figures is an optional fifth column so option cards can show cost, effort and thresholds as bullets.
- **Steps tab** on the Pipeline: one row per planned step (Pipeline ID, Step, Task, Specialist, Status Planned/Done/Skipped). Next step stays a one-line question. The planner writes the rows; the supervisor marks completed steps Done.
- **Decision page** reads both tabs. Options render as cards with key-figure bullets and the recommended one marked; the reason renders as bullets; planned steps as a numbered list. Without rows it falls back to the text: option codes (now also `Proposed (Option B):` and lettered `Alternatives: A …; C …`) and a numbered Next step.
- **Revise** (`revise` in `workflow.yaml`, `revise()` in `Rules.js`, `reviseDecisionReview` in `WebApp.js`): the founder can change an item's current, already decided decision while the item is Approved, Rework, Parked, Rejected or Completed. The decision row keeps its ID; Status becomes the new outcome, the reason is appended to Reason and the revision to Review source; the item moves as that outcome would from review.
- `workflow.yaml` gains the `revise` transition and section and a `tabs` schema. Skills (planner, supervisor, runs and records references, research linking rules, technical assessment output, GTM) write and read the new tabs.

## Rationale
- Child tabs keyed by permanent ID keep Master readable without new columns and follow HOR-6: rows are found by ID, never position.
- Revising in place, rather than adding a decision row, avoids allocating a Decision ID from Apps Script, which can't call `reserve_id`; the appended reason and Review source keep the trail. A new review round still gets a new row from an agent.
- The text fallback keeps the page correct for decisions written before the tabs existed.

## Impact
- Live sheets (29/10/2026): Decision Register **Options** tab and Pipeline **Steps** tab added with headers (additive; no existing tab or column changed). Options rows backfilled for proposed Decisions 5, 6, 7 and 9. Decisions 2 and 8 name one or no option codes and stay on the text fallback. Their Decision cells were not shortened.
- The document-graph sync reads only the Master tabs, so Options and Steps aren't in Neon or `get_item_history`.
- A revise to Ready isn't coordinated with `claim_item`: revising an Approved, Ready item while a session is claiming it is a small race. The page refuses Researching items.

## Verification
- `npm test` in `google_appscript/pipeline-decisions`: 34 tests, including revise rules, the revise web flow, Options and Steps tabs and their fallbacks.
- `.venv/bin/python -m pytest tests/unit -q`: 460 passed, including new checks that `Rules.js` and `WebApp.js` match `workflow.yaml`'s `revise` and `tabs`.
- The page was rendered offline in Chromium with stubbed data (proposal with option cards, decided record with Revise form). Not yet deployed.

## Follow-Ups
- Founder: push and deploy the Apps Script project (runbook: [Apps Script projects, Deploy the web page after a change](../../runbook/subscription-agents/clasp.md#deploy-the-web-page-after-a-change)), then republish the workflow and specialist skills.
- Optionally shorten the Decision cells of Decisions 5, 6, 7 and 9 to one line now that their options are on the Options tab, and add Options rows for Decision 2 if wanted.
- Add the Options and Steps tabs to each workbook's Read Me tab.
