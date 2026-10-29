# Web workspace Triage board redesign (HOR-12 c, item 52)

## Context

Item 51 ([note](2026-10-29_web-workspace-scale-and-ux_note.md)) made the Horology web workspace (`google_appscript/pipeline-decisions`) fast but kept its look. On 30/10/2026 the founder chose direction B, **Triage board**, from mockups: a dark top bar, a decisions inbox beside a reading pane, and a Pipeline board by workflow column. Item 52 builds it on the implementation route (run R-27).

## Decision

- **Look.** IBM Plex Sans (Google Fonts, with system fallbacks), ground `#eef1f3`, ink `#1e2a32`, accent `#0f5f73`, white panels with a 1px `#d5dde2` border and 8–10px corners. Tokens and the shared buttons, inputs and pills moved to `shared-ui/theme.css` and `controls.css`; the earlier stacked dark-theme overrides in `Review.html` were removed.
- **Top bar.** Decisions (with the number needing review), Pipeline, Folders; one search box for the view on screen; the amber **Add item** button (`#f2b33d`, dark text).
- **Decisions.** Inbox (Needs review / History; Decision ID, domain, age, title, one-line question; accent bar on the open row) beside a reading pane: header line, title, Question, proposal, Options as cards with RECOMMENDED on the accent-bordered one, Why bullets, planned steps, and a **Your decision** panel with the existing outcome or revise form and links. For a proposal the option cards are the radio choice; non-approve outcomes disable them instead of hiding them. Opening a decision still reads it fresh and sets `#decision/<ID>`.
- **Pipeline.** Board columns Inbox; Investigating or planning; Waiting for you; Building or delivering; Done (Completed, most recently updated first, 10 shown). Parked and Rejected are under **Show**, which also lists all items as cards. Domain and Type filters, Type offering **Build** (Feature, Enhancement, Refactor, Fix) and **Investigate** (the rest); cards show `#ID · domain`, a coloured Type tag, title and stage or current decision. Rework and Researching items are placed by Stage (Stage 3 builds, earlier investigates), so no item falls off the board.
- **Server.** One addition: each decision summary carries `date` (Decision Date, or the item's Updated date for a proposal) for the inbox age. Writes, version checks, revise, caching and the embedded first list are unchanged.
- **Replaced from item 51:** the Cards/Rows toggle and status chips. The board columns and their counts do that job; Status remains under **More filters** and all items are still one choice away under **Show**.

## Verification

- `npm test` in `google_appscript/pipeline-decisions` (52 decision tests and the folder test) and `python -m pytest tests/unit -q` pass. New tests cover the inbox lists, the age labels, board column placement, the Build/Investigate Type groups and the summary `date`.
- Headless Chromium against the page with a mocked `google.script.run`, at 1400px and 390px: every view renders without script errors; opening a decision, a card, Edit item, Back, Folders and Add item work; no visible control is under 44px; no horizontal page scroll at phone width (the board scrolls inside itself).
- Contrast of every text colour pair used is at least 5.5:1 (muted `#4f5d66` on the column ground is the lowest).
- Not verified: the live deployment and Google Fonts loading inside the Apps Script sandbox; the font falls back to the system sans-serif if blocked.

## Impact

- `Review.html`, `WebApp.js`, `shared-ui/theme.css`, `shared-ui/controls.css`, generated `SharedUi.html`; `tests/test-decisions.cjs`.
- Docs: [Apps Script projects](../../architecture/subscription-agents/apps-script.md#founder-review-web-page) and the [clasp runbook](../../runbook/subscription-agents/clasp.md#deploy-the-web-page-after-a-change) checks.

## Follow-Ups

- Founder or coordinating session: after merge, from `google_appscript/pipeline-decisions` run `npm test` and `npm run clasp:push`, deploy a new version of the existing web-app deployment and run the runbook checks, including a phone-width check.
