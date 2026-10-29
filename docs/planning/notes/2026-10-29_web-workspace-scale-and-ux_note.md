# Web workspace scale and usability (HOR-12 c, item 51)

## Context

The Horology web workspace (`google_appscript/pipeline-decisions`) loaded every Pipeline Master row with all its long text in one call, and every decision as a full review record (proposal, reason, options, steps, links) in another. That worked at about 20 items and 10 decisions but grows linearly with the registers. The founder changed item 51 from an assessment to a build on 29/10/2026: keep the workspace fast as the registers reach hundreds of rows, and make it easier to use. The document graph view (item 45) is out of scope.

## Measured before and after

Synthetic workbooks with the live sheets' text lengths (29/10/2026: Summary about 450 characters, Next step about 1,300, Decision and Reason about 800 each, three Options and four Steps rows per record), run through the server functions offline. Size is the JSON a call returns; range reads are `getDataRange` reads.

| Call | Today's size (17 items, 9 decisions) | 300 items, 300 decisions |
|---|---|---|
| Decisions list, before | 70.7 KB, 5 workbook opens, 5 reads | 2,359 KB, 5 opens, 5 reads |
| Decisions list, after | 3.4 KB, 2 opens, 3 reads | 114 KB, 2 opens, 3 reads; 0 reads from cache |
| Pipeline list, before | 100.2 KB, 2 opens, 2 reads | 1,771 KB, 2 opens, 2 reads |
| Pipeline list, after | 8.3 KB, 1 open, 1 read | 147 KB, 1 open, 1 read; 0 reads from cache |
| Open one decision (new) | 7.8 KB, 2 opens, 5 reads | 7.8 KB |
| Open one item (new) | 5.9 KB, 1 open, 2 reads | 5.9 KB |

The first Decisions list now arrives inside the page, saving one `google.script.run` round trip before first paint. Live timings were not measured: nothing was deployed.

## Decision

- **Light lists, details on open.** `getReviewDashboard` returns decision summaries and reads only the Masters; `getDecisionReview(id)` returns one full record, fresh. `getPipelineOverview` returns `{rows}` with list fields and a one-line summary; `getPipelineItem(id)` returns one full item with Steps and its edit version, fresh. `searchPipelineItems(query)` searches the long text on the server so search still finds words in Next step and Summary.
- **Fewer reads.** `openBook` opens each workbook once per request.
- **Short list cache.** The two lists are cached for 60 seconds in the script cache, in 30,000-character chunks (under the 100 KB per-key limit even at three bytes a character), cleared by every write from the page and bypassed by **Refresh**. Details are never cached, so the existing version checks still compare against the sheet. Safe because the deployment runs as the owner and only the owner can open it.
- **First paint.** `doGet` embeds the first Decisions list; the Pipeline list loads in the background after it.
- **Usability.** URL-hash navigation through `google.script.history` (Back works; `#item/51` and `#decision/9` can be bookmarked); links between a decision and its item; loading and error states with **Try again**; Decisions search; Pipeline status chips with counts, sort, word-by-word search and 50-at-a-time lists with **Show more**; `/` focuses search.
- **Unchanged:** every write path (rows found by ID just before writing, version checks, revise, Options and Steps tabs, Status written last), spaced paragraphs, the item title as the decision heading, the Folders and Add item views.

## Rationale

Payload size was the cost that grows with the registers; the light list cuts it by about 15 times at 300 rows and keeps opening one record constant. Server-side paging was not needed: at 300 rows the light lists are 114–147 KB and filter instantly in the browser, and paging would have broken the client-side filters and counts. The cache is short and cleared on every page write because agents and the founder also edit the sheets directly, which the script cannot see.

## Impact

- `WebApp.js`, `WebItems.js`, `Registers.js`, `Apply.js`, `Folders.js` (shared `openBook`), `Review.html`; tests in `tests/test-decisions.cjs` (light lists, fresh details, full-text search, cache chunks and invalidation, embedded list escaping, routing, search and sort) and `tests/test-folders.cjs`.
- Docs: [Apps Script projects](../../architecture/subscription-agents/apps-script.md#founder-review-web-page) and the [clasp runbook](../../runbook/subscription-agents/clasp.md#deploy-the-web-page-after-a-change) checks.
- A sheet edit by an agent or the founder can take up to a minute to show in a list (not in an opened record).

## Follow-Ups

- Founder: from `google_appscript/pipeline-decisions`, `npm test` and `npm run clasp:push`, then deploy a new version of the existing web-app deployment and run the checks in the runbook.
- If the registers pass about 1,000 rows, revisit server-side filtering for the Pipeline list (the light list would pass about 500 KB).
