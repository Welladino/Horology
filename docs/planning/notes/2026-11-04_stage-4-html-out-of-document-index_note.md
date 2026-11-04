# Stage 4 HTML out of the Document Index

## Topic

- stage-4-html-out-of-document-index

## Context

Every Stage 4 page's Drive HTML copy got a reserved Document ID and a Document Index row (`horology-synthesis-artifacts` step 8; `visuals-and-pages.md` called the Drive HTML and its Index entry canonical; supervisor step 9 checked for that row). Since item 70 the Pages tab lists the published pages, so the HTML rows duplicated it. The founder decided on 04/11/2026 (Pipeline item 71, HOR-9) to keep the HTML out of the Index and to show the Implementation report template's metadata as a table.

## Decision

- **The Stage 4 HTML is still saved to the Synthesis folder** (so it can be republished) but gets no Document Index row and no reserved Document ID. Its source, the Stage 3 deliverable or the Implementation report, is the indexed record. A visual Google Doc or Sheet used instead of HTML is a document and is still indexed.
- **The Pages tab's Document ID is the page's source document**: the Stage 3 deliverable, or the Implementation report on the implementation route. The tab is otherwise unchanged (no Drive file column; published pages only).
- **The Implementation report template's metadata block is a two-column table** (Field, Value), with the bracketed guidance kept as the values.

## Changes

- `horology-synthesis-artifacts` steps 3, 8, 9 and 10 and `references/visuals-and-pages.md` (canonical-record sentence, redeploy step, Pages tab Document ID and Title rows).
- Supervisor item-mode step 9 and implementation-route step 4 verify the HTML in the Synthesis folder, not an Index row.
- `horology-mcp-access` private pages: the source document is the record; the Pages row carries its Document ID.
- `workflow.yaml` wording for `synthesize-stage-3` and `complete-implementation` (no rule change, version stays 4); digest missing-records check now looks for the page in the Synthesis folder and flags a new Index row for Stage 4 HTML.
- Standing docs: workspace records, workflow operations.
- Tests: `test_stage_4_html_gets_no_document_index_row` and `test_pages_tab_document_id_is_the_source_document` in `tests/unit/workflow/test_skill_files.py`; they fail on the old wording.
- Codex versions: horology-workflows 0.6.13, horology-specialists 0.2.13, horology-tools 1.0.3.

## Live changes

- Document Index rows for Documents 24, 33, 40 and 45 (Stage 4 HTML of items 22, 45, 53 and 69) were deleted after each was found by Document ID and confirmed as a `text/html` Drive file. Their IDs stay retired; the files stay in Drive.
- Pages tab: item 69's row now points at Document 44 (its Implementation report) and item 45's at Document 34 (the Drive copy of its Stage 3 plan; Document 32 was the repository note and Document 31 the Stage 1 assessment).
- Implementation report template: metadata block replaced by a 14-row, two-column table (header row plus the 13 fields); the rest of the template is unchanged.
