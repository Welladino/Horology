---
name: horology-synthesis-artifacts
description: Create a concise, visual Stage 4 synthesis artifact immediately after a Pipeline item's Stage 3 specialist deliverable, in the same supervisor run and before founder review.
---

# Horology Synthesis Artifacts

The supervisor invokes this specialist as the final step of a Stage 3 run. Stage 4 needs no new founder prompt, Ready selection or schedule. The founder reviews the combined Stage 3 deliverable and Stage 4 artifact afterward. This skill does not accept a proposal, authorise implementation or send email.

## Inputs and ownership

1. Receive the Pipeline ID and active run ID from the supervisor. The supervisor owns `claim_item` and `finish_run`; do not claim or finish that run again. For a standalone recovery request, first check the live row and Document Index, then claim and finish exactly one separate run.
2. Read the live Pipeline, Decision Register and Document Index by header name. Read the Stage 3 deliverable, prior investigation, earlier decisions and source documents. Prefer the latest nonsuperseded documents. Treat a proposed decision as **pending founder review**; never present it as accepted.
3. Check Document Index for a Stage 4 artifact tied to this Pipeline ID and current proposed Decision ID or Stage 3 deliverable. Reuse a verified artifact instead of duplicating it. If the Stage 3 source changes materially, create a new version with `Supersedes document ID`.
4. Read [locations](../horology-research/references/locations.md) and the Pipeline Locations tab. Use only the Synthesis folder for the item's Domain and Entity; place supporting assets in its Assets folder.

## Visual briefing

5. Lead with the proposed outcome, the decision the founder needs to make and the current status. Prefer a self-contained HTML briefing when it can be saved and opened reliably. Use a visual Google Doc, Sheet or a useful combination when that serves the material better. Keep the first view brief: a clear headline, a simple process or comparison graphic, three to five evidence cards, the main tradeoff and the next action. Put detailed rationale, uncertainties and source links lower down or behind expandable sections. Design for mobile and print, with readable contrast and text alternatives for visual meaning. Do not create a text-heavy document and call it a visual synthesis.
6. Use images or charts when they clarify the evidence or comparison. Python is allowed for chart generation: choose a chart that answers the actual question, make it legible and visually polished, and export a static SVG or high-resolution PNG that works in HTML and print. Use real figures only where sources support them; label units, dates, estimates and uncertainty. Do not invent measurements or draw a chart from qualitative claims. Bundle permitted source images and chart assets with the HTML rather than relying on temporary third-party or private Drive image URLs. Provide alt text and source attribution. Follow [visual and private publishing guidance](references/visuals-and-pages.md).
7. Show what Stage 1 found, what Stage 2 authorised, what Stage 3 produced, the proposed choice and any unresolved question. Include direct links to source documents and Decision Register. The artifact is a presentation of the work, not a new recommendation or decision.
8. Save and verify every principal output in the matching Synthesis folder. Register it in Document Index with Pipeline ID, current decision ID in the title, reading order, source link, type and status. A proposal remains `draft` until the founder approves it. Do not create or change a Decision Register decision.
9. When the founder's private Cloudflare Pages project and deployment access are configured, offer the HTML briefing at a stable, Access-protected URL following [the publishing procedure](references/visuals-and-pages.md). Keep the Drive artifact and Document Index row as the records. Publishing is optional: an unavailable or unverified Pages setup must not prevent a verified Drive synthesis or Stage 4 transition. Never publish through a public Pages URL or widen an Access policy to make deployment work.
10. Return verified Drive and, if published, private Pages links plus unresolved gaps to the supervisor. The supervisor then moves the item directly from Stage 3 to **Stage 4**, Status **Awaiting decision**, Review stage **Specialist deliverable**, Agent status **No action**, while preserving Current decision ID and the substantive Next step. Only advance after Drive outputs and Index rows are verified. If synthesis creation fails, leave Stage 3 in place and report the failure; report a publishing failure separately.
