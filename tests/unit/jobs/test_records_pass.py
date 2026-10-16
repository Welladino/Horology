"""The sync job's records pass: parsing the three registers, and where it runs. No network or database."""
import asyncio
import sys
from unittest.mock import AsyncMock, patch

from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import records  # noqa: E402

PIPELINE = [
    ["ID", "Title", "Domain", "Status", "Agent status", "Agent type", "Run location", "Planner output",
     "Next step / Research question", "Created"],
    [42.0, "Pricing page", "Welladino", "Inbox", "Ready", "Claude Code", "", "No", "Which tier first?", 46304],
    ["", "No ID", "Welladino", "Inbox"],  # skipped: no permanent ID
    ["x7", "Bad ID"],  # skipped: not a number
    [],  # blank row
]
DECISIONS = [
    ["Decision ID", "Pipeline ID", "Status", "Review stage", "Rework instructions"],
    ["D-3", "42", "proposed", "Stage 1", ""],
]
INDEX = [
    ["Document ID", "Pipeline ID", "Title", "Drive URL", "Document Type", "Graph Inclusion", "Last Updated"],
    [7, 42, "Pricing research", "https://docs.google.com/document/d/abcdefghijk/edit", "research", True, 46305],
    [8, "", "Brand guide", "", "brand_guide", False, ""],
]


def test_books_accept_the_old_and_new_forms():
    assert records.books_for("1kOb") == {"index": "1kOb"}
    assert records.books_for({"index": "a", "pipeline": "b", "decisions": "c", "other": "x"}) == \
        {"index": "a", "pipeline": "b", "decisions": "c"}


def test_pipeline_rows_become_items():
    items = records.pipeline_items(PIPELINE)
    assert [i["pipeline_id"] for i in items] == ["42"]
    item = items[0]
    assert item["status"] == "Inbox" and item["agent_status"] == "Ready" and item["agent_type"] == "Claude Code"
    assert item["run_location"] is None  # blank means Local; stored as no value
    assert item["next_step"] == "Which tier first?"
    assert item["data"]["Created"] == "2026-10-09"  # unformatted day number -> ISO date


def test_decisions_and_index_rows_are_parsed():
    assert records.decisions(DECISIONS) == [{
        "decision_id": "D-3", "pipeline_id": "42", "status": "proposed", "review_stage": "Stage 1",
        "decision": None, "reason": None, "rework_instructions": None,
        "data": {"Decision ID": "D-3", "Pipeline ID": "42", "Status": "proposed", "Review stage": "Stage 1",
                 "Rework instructions": ""}}]
    rows = records.index_rows(INDEX)
    assert [(r["index_document_id"], r["pipeline_id"], r["graph_inclusion"]) for r in rows] == \
        [("7", "42", True), ("8", None, False)]
    assert rows[0]["last_updated"] == "2026-10-10"


def test_without_a_pipeline_or_decision_register_the_pass_is_skipped():
    result = asyncio.run(records.run(None, "ws", {"index": "abc"}))
    assert "skipped" in result


def test_records_mode_and_the_sync_run_the_pass():
    from graph_sync import __main__ as job
    books = {"index": "i", "pipeline": "p", "decisions": "d"}
    google = object()
    with patch.object(job.runs, "claim", AsyncMock(return_value=None)), \
            patch.object(job.runs, "finish", AsyncMock(return_value=None)), \
            patch.object(job.records, "run", AsyncMock(return_value={"items": 1})) as run, \
            patch.object(job, "sync_workspace", AsyncMock(return_value={"deferred": 0})) as sync, \
            patch.object(job.review_tab, "run", AsyncMock(return_value={"extraction": {"remaining": 0}})):
        assert asyncio.run(job.run_workspace(google, "ws", books, "records", 1)) == {"records": {"items": 1}}
        sync.assert_not_awaited()
        result = asyncio.run(job.run_workspace(google, "ws", books, "sync", 1))
    assert result["records"] == {"items": 1}
    sync.assert_awaited_once_with(google, "ws", "i")  # the document import still gets the Document Index id
    assert run.await_count == 2


def test_a_failing_records_pass_never_blocks_the_import():
    from graph_sync import __main__ as job
    with patch.object(job.runs, "claim", AsyncMock(return_value=None)), \
            patch.object(job.runs, "finish", AsyncMock(return_value=None)), \
            patch.object(job.records, "run", AsyncMock(side_effect=RuntimeError("sheet gone"))), \
            patch.object(job, "sync_workspace", AsyncMock(return_value={"deferred": 0})) as sync, \
            patch.object(job.review_tab, "run", AsyncMock(return_value={"extraction": {"remaining": 0}})):
        result = asyncio.run(job.run_workspace(object(), "ws", {"index": "i", "pipeline": "p"}, "sync", 1))
    assert "failed" in result["records"]
    sync.assert_awaited_once()
