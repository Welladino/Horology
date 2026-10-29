# Default visuals in agent documents (HOR-11)

## Topic
- default-document-visuals

## Context
- Pipeline item 48, run R-19. Agent documents rarely had visuals: the shared presentation rules said to add one "only when" clearer than text, and the Research, Direction and Plan templates marked Visuals as optional. Only the Technical Assessment required one (the effort–uncertainty quadrant).
- Item 45's run (R-17) could not embed its quadrant: Docs `insertInlineImage` needs a URI Google can fetch, so it linked the SVG from Drive instead.

## Hands-on check of image routes (29/10/2026, Drive and Docs connectors, scratch Docs trashed afterwards)
- Private Drive PNG through `https://drive.google.com/uc?export=view&id=…`: refused, "The provided image should be publicly accessible".
- HTML upload with a `data:image/png;base64` `<img>`, converted to a Google Doc by Drive `create_file`: image embedded.
- That embedded image's `contentUri` passed to `insertInlineImage` in a separate, existing Doc: inserted, and still present after the carrier Doc was trashed.
- A `data:` URI passed straight to `insertInlineImage`: inserted for a 127-byte PNG. Google documents a 2 KB URI limit, so this suits only tiny images; not tested above it.
- Not tried: a public share (rejected on privacy grounds; the share tool only grants users or groups anyway), a linked Sheets chart (the Docs API has no request to insert one) and Apps Script `DocumentApp` with a blob (needs a deployed script endpoint; possible later, not needed now).

## Decision
- Each document type has a default visual: Research, an options or evidence chart from real figures; Direction, an audience or positioning diagram; Plan, a milestone timeline or process flow; Technical Assessment, the quadrant plus a current-vs-proposed diagram.
- Skipping one needs a `No visual: <reason>` line in the Visuals section.
- The supervisor's result check fails a Stage 1 or Stage 3 document with neither, sends it back once, then fails the run.
- Images go in through the carrier-Doc route; a linked PNG with a caption is the reported fallback.

## Impact
- `references/presentation.md` (research and digest copies, kept identical by the unit test), research, GTM, marketing strategy, content planner, security review and technical assessment skills, technical assessment `output.md`, supervisor `SKILL.md` and `references/routing.md`.
- Runbook: "Insert an image into a private Google Doc" in `docs/runbook/subscription-agents/workflow_operations.md`.
- Template originals (Templates tab): Research, Direction and Plan "Visuals (optional)" renamed to "Visuals" with the default visual and `No visual:` rule in the placeholder; Technical Assessment gains a "Current vs proposed" subsection beside the quadrant.
- `workflow.yaml` is unchanged: no workflow state moved.

## Follow-Ups
- Republish the skills so claude.ai and Codex installs pick up the new rules.
- Item 45's assessment still links its quadrant; it can be embedded by this route on its next revision.
