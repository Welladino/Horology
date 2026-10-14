"""Sync job rules that need no database: Document Index parsing, batched status writes, follow-up runs."""
import asyncio
import sys
from unittest.mock import AsyncMock, patch

import pytest

from support.document_index import FIELD_HEADER, HEADER, field_row, row
from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import index, sync  # noqa: E402


class TestParse:
    def test_reads_rows_booleans_and_numeric_ids(self):
        rows, headers = index.parse([HEADER, row(1.0, "A", "fileAAAAAAAAAA", True), row("2", "B", "fileBBBBBBBBBB", "FALSE"), [""]])
        assert [(r.index_id, r.included, r.row_number) for r in rows] == [("1", True, 2), ("2", False, 3)]
        assert index.status_range(headers, 3) == "'Document Index'!M3:O3"

    def test_rejects_missing_columns_and_duplicate_ids(self):
        with pytest.raises(ValueError, match="missing columns"):
            index.parse([["Document ID", "Title"]])
        with pytest.raises(ValueError, match="duplicate"):
            index.parse([HEADER, row("1", "A", "fileAAAAAAAAAA", True), row("1", "B", "fileBBBBBBBBBB", True)])

    @pytest.mark.parametrize("url,expected", [
        ("https://drive.google.com/file/d/1dVL5q-M50QyygZbm4Z7sf93n1h-JOidg/view?usp=drivesdk", "1dVL5q-M50QyygZbm4Z7sf93n1h-JOidg"),
        ("https://docs.google.com/document/d/1JoIx28klbity_yornzvw8SNJ9hm-18Kj-rCwtVfZ4WU/edit", "1JoIx28klbity_yornzvw8SNJ9hm-18Kj-rCwtVfZ4WU"),
        ("https://drive.google.com/open?id=1abcdefghijKLMN", "1abcdefghijKLMN"),
        ("https://example.com/not-drive", None),
    ])
    def test_drive_file_id(self, url, expected):
        assert index.drive_file_id(url) == expected

    def test_column_letters(self):
        assert [index.column_letter(i) for i in (0, 12, 25, 26)] == ["A", "M", "Z", "AA"]


class TestFieldParsing:
    def test_optional_columns_are_read_when_present(self):
        rows, _ = index.parse([FIELD_HEADER, field_row("1", "fileAAAAAAAAAA", "Newsletter", "Daily Brief", 12.0)])
        assert (rows[0].domain, rows[0].business_entity, rows[0].pipeline_id) == ("Newsletter", "Daily Brief", "12")

    def test_a_workbook_without_them_still_parses(self):
        rows, _ = index.parse([HEADER, row("1", "A", "fileAAAAAAAAAA", True)])
        assert (rows[0].domain, rows[0].pipeline_id) == ("", "")


def test_a_failed_mid_run_status_write_is_kept_for_the_next_one():
    from types import SimpleNamespace

    class FlakyGoogle:
        def __init__(self):
            self.calls, self.fail = [], True

        async def write_cells(self, spreadsheet_id, updates):
            if self.fail:
                self.fail = False
                raise RuntimeError("quota")
            self.calls.append(list(updates))

    async def run():
        google = FlakyGoogle()
        headers = {name: i for i, name in enumerate(HEADER)}
        writer = sync._StatusWriter(google, "sheet", headers)
        for n in range(sync.STATUS_BATCH + 1):
            await writer.add(SimpleNamespace(row_number=n + 2), ("unchanged", n, "1"))
        await writer.finish([])
        assert [len(call) for call in google.calls] == [sync.STATUS_BATCH + 1]  # nothing lost
    asyncio.run(run())


class TestFollowUps:
    def test_which_run_comes_next(self):
        from graph_sync.__main__ import follow_up_mode
        assert follow_up_mode("sync", {"deferred": 4, "entities": {"extraction": {"remaining": 0}}}) == "sync"
        assert follow_up_mode("sync", {"deferred": 0, "entities": {"extraction": {"remaining": 9}}}) == "entities"
        assert follow_up_mode("sync", {"deferred": 0, "entities": {"extraction": "failed"}}) is None
        assert follow_up_mode("entities", {"extraction": {"remaining": 1}}) == "entities"
        assert follow_up_mode("entities", {"extraction": {"remaining": 0}}) is None
        assert follow_up_mode("topics", {"topics": 12}) is None

    def test_the_claim_is_confirmed_then_handed_to_the_follow_up(self):
        from graph_sync import __main__ as job
        with patch.object(job.runs, "claim", AsyncMock(return_value=None)) as claim, \
                patch.object(job.runs, "finish", AsyncMock(return_value="op")) as finish, \
                patch.object(job, "sync_workspace", AsyncMock(return_value={"deferred": 2})), \
                patch.object(job.review_tab, "run", AsyncMock(return_value={"extraction": {"remaining": 0}})):
            result = asyncio.run(job.run_workspace(None, "test-ws", "sheet", "sync", 2, "tok"))
        claim.assert_awaited_once_with("test-ws", "sync", 2, "tok")
        finish.assert_awaited_once_with("test-ws", "sync", "sync", 2)
        assert result["follow_up"] == "started sync run 3"

    def test_a_workspace_already_running_is_skipped(self):
        from graph_sync import __main__ as job
        with patch.object(job.runs, "claim", AsyncMock(return_value="entities")), \
                patch.object(job, "sync_workspace", AsyncMock()) as work:
            result = asyncio.run(job.run_workspace(None, "test-ws", "sheet", "sync", 1))
        assert result == {"workspace": "test-ws", "skipped": "entities run in progress"}
        work.assert_not_awaited()

    def test_released_even_when_the_run_fails(self):
        from graph_sync import __main__ as job
        with patch.object(job.runs, "claim", AsyncMock(return_value=None)), \
                patch.object(job.runs, "release", AsyncMock()) as release, \
                patch.object(job.topics, "rebuild", AsyncMock(side_effect=RuntimeError("down"))):
            with pytest.raises(RuntimeError):
                asyncio.run(job.run_workspace(None, "test-ws", "sheet", "topics", 1))
        release.assert_awaited_once_with("test-ws", "topics")
