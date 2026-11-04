# Drive-only Research Links

## Context

The Implementation questions on Pipeline items 55 and 59 (Decisions 13 and 14) put GitHub links in the Decision Register's Research Links: a compare link and a repository planning note on a working branch. No skill said what Research Links may hold, and the Drive-first rule ([Drive-first agent documents](2026-11-02_drive-first-agent-documents_note.md)) covered only the Document Index. Both branches were later merged and deleted, so both links stopped resolving. The founder decided on 04/11/2026 (item 68, HOR-9) that Research Links holds Drive files only. This is a direct fix, with no investigation.

## Decision

- **Research Links holds Drive files only:** Google Docs, Sheets or Slides, or an HTML file saved in Drive, one per line. Never a GitHub compare, commit, branch, pull request or repository-file link, a Drive folder or a web page.
- **Repository evidence gets a Drive document.** It copies or summarises the repository file and names the repository, branch and commit. The repository file stays in the repository; its GitHub link goes in the document's Related Repo Document in the Document Index.
- **The service enforces it.** `check_register_write` takes `research_links` for a Decision Register write and returns `ok: false`, reason `research_links_not_drive`, with the offending links, before any ownership check or binding. Passing `research_links` for the Document Index is an error. The check accepts `docs.google.com/{document,spreadsheets,presentation}/d/<id>`, `drive.google.com/file/d/<id>` and `drive.google.com/open?id=<id>` over HTTPS; it refuses Drive folders and look-alike hosts.

## What changed

- Skills: `horology-research/references/linking.md` (the rule, and `research_links` in the ownership step), `horology-technical-assessment/references/output.md`, `horology-capture-triage/references/records.md`, `horology-supervisor/SKILL.md` (an Implementation question saves its findings to a Drive document first) and `horology-document-graph/SKILL.md`. Codex plugin versions bumped: workflows 0.6.11, specialists 0.2.10, document-graph 1.0.3.
- Service: `graph_core/history/service.py` (`is_drive_file`, `research_link_problems`, the `research_links` check) and the `check_register_write` tool in `mcp-servers/document-graph`.
- Docs: [workspace records](../../architecture/subscription-agents/workspace-records.md) and [document-graph MCP](../../architecture/mcp/document-graph.md#register-ids).
- Live records (04/11/2026, run R-67): Documents 41 (Decision 13, item 55 evidence from commits 546e136f, 82435ec9 and merge be24f161) and 42 (Decision 14, a copy of the item 59 planning note, with its repository copy on `version_v1.8` in Related Repo Document) in the Article Aggregator technical research folder, and Decisions 13 and 14 relinked to them. Neither fits an existing template, so both are plain Google Docs. Their IDs were reserved without a Pipeline item, because `reserve_id` ties an item's reservation to the live run holding that item and R-67 holds item 68.

## Verification

- `.venv/bin/python -m pytest tests/unit -q`: 481 passed. New cases in `tests/unit/document_graph_core/test_history_rules.py` cover Docs, Sheets, Slides, Drive file and `open?id=` links passing, and GitHub, Drive folder, look-alike host, plain HTTP and web links refused.
- Not verified live: the deployed document-graph service still has the old tool until it is redeployed, so its `check_register_write` ignores `research_links`.

## Founder steps

1. Redeploy the document-graph service ([runbook](../../runbook/gcp/mcp_deployment.md)), then check the tool lists `research_links`.
2. Rebuild and upload the changed skills on claude.ai ([runbook](../../runbook/subscription-agents/claude_skills.md)) and rebuild the Codex plugins: `python3 scripts/ops/claude/build_skill_zips.py horology-capture-triage horology-content-planner horology-gtm horology-marketing-strategy horology-planner horology-research horology-security-review horology-supervisor horology-synthesis-artifacts horology-technical-assessment horology-document-graph`.
3. Decisions 1 and 3 hold a document title as text in Research Links instead of a link; replace each with its Drive link (Documents 16 and 19) if wanted.
