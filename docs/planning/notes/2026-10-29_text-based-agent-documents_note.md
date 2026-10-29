# Implementation Note

## Topic
- text-based-agent-documents

## Context
- HOR-11 (Pipeline item 48) proposed a default visual in every Research, Direction, Plan and Technical Assessment document. Its run found that Docs `insertInlineImage` refuses private Drive URLs; the only private route uploads the image as base64 through the agent (a carrier Doc), which costs tens of thousands of output tokens per chart and relies on undocumented behaviour.
- The Technical Assessment's effort–uncertainty quadrant had the same problem: item 45's run linked the image instead of embedding it.

## Decision
- Agent documents are text-based. Comparisons, ratings, timelines and flows are native tables and numbered lists; documents don't carry images or charts.
- Charts and diagrams belong in the Stage 4 synthesis artifact (`horology-synthesis-artifacts`, published to Cloudflare Pages).
- The Technical Assessment quadrant image is replaced by a ratings table (Option, Effort, Uncertainty, Recommended, Reason). `scripts/render_quadrant.py` is removed.
- The HOR-11 commits (4916a2a, 28880e8) are reverted and item 48 is rejected.

## Rationale
- Native tables carry the same information as the ordinal quadrant (nine possible positions) and the reasons too, at no image cost.
- The synthesis artifact is already HTML with Python-generated charts, where images cost nothing to place.

## Impact
- `presentation.md` (research and digest copies), research and technical-assessment skills and the TA output rules.
- Drive templates: the Technical Assessment template's quadrant image is replaced by the ratings table; the Research, Direction and Plan templates lose their optional Visuals sections.

## Follow-Ups
- If Stage 1 documents need images later, an Apps Script that inserts a Drive blob (`DocumentApp` `insertImage`) from a placeholder is the private, low-token route; it needs the `documents` scope.
