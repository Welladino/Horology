"""Document Index -> graph sync job.

Parsing tests need nothing. The end-to-end test runs the real sync against a
disposable migrated Postgres as the restricted horology_graph login
(GRAPH_TEST_RUNTIME_URL), with a fake Google client and a fake embedding, so
it also proves that login's grants are enough.
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "mcp-servers" / "document-graph"))  # append: the gateway also has a server.py
sys.path.append(str(ROOT / "jobs" / "document-graph-sync"))

from graph_sync import index, sync  # noqa: E402
from document_graph import graph  # noqa: E402
from document_graph.integrations.openrouter import client as openrouter  # noqa: E402

HEADER = ["Document ID", "Pipeline item", "Sequence", "Title", "Drive URL", "Workspace", "Domain", "Entity",
          "Document Type", "Document Status", "Last Updated", "Graph Inclusion", "Graph Sync Status",
          "Graph Document ID", "Last Synced Revision", "Related ClickUp URL", "Related Repo Document",
          "Related Pipeline URL", "Supersedes document ID", "Pipeline ID"]


def row(doc_id, title, file_id, included, doc_type="plan", workspace="test-ws", supersedes=""):
    cells = [""] * len(HEADER)
    cells[0], cells[3], cells[5], cells[8], cells[11], cells[18] = doc_id, title, workspace, doc_type, included, supersedes
    cells[4] = f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"
    return cells


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


class FakeGoogle:
    def __init__(self, values, files):
        self.values, self.files, self.writes, self.downloads = values, files, [], []
    async def sheet_rows(self, spreadsheet_id, tab):
        return self.values
    async def write_cells(self, spreadsheet_id, updates):
        self.writes = updates
    async def file_metadata(self, file_id):
        if file_id not in self.files:  # Drive hides unshared files as 404
            import httpx
            request = httpx.Request("GET", "https://www.googleapis.com/drive/v3/files/" + file_id)
            raise httpx.HTTPStatusError("404", request=request, response=httpx.Response(404, request=request))
        mime, version, text = self.files[file_id]
        return {"id": file_id, "mimeType": mime, "version": version, "size": str(len(text))}
    async def file_text(self, meta):
        self.downloads.append(meta["id"])
        return self.files[meta["id"]][2]


@pytest.fixture
def database():
    dsn = os.environ.get("GRAPH_TEST_RUNTIME_URL")
    if not dsn:
        pytest.skip("Disposable migrated Postgres with the horology_graph login is required")
    return dsn


def test_sync_imports_skips_unchanged_removes_and_writes_status(database):
    from horology_runtime.database import Database
    files = {"fileAAAAAAAAAA": ("text/markdown", "1", "# Pricing plan\nCharge per seat."),
             "fileBBBBBBBBBB": ("text/markdown", "4", "# Pricing v2\nCharge per workspace."),
             "fileCCCCCCCCCC": ("application/vnd.google-apps.spreadsheet", "1", "")}
    google = FakeGoogle([HEADER,
                         row("1", "Pricing plan", "fileAAAAAAAAAA", True),
                         row("2", "Pricing v2", "fileBBBBBBBBBB", True, supersedes="1"),
                         row("3", "A register", "fileCCCCCCCCCC", True, doc_type="guide"),
                         row("4", "Other workspace", "fileAAAAAAAAAA", True, workspace="other-ws"),
                         row("5", "Not shared", "fileZZZZZZZZZZ", True)], files)
    embed = AsyncMock(return_value=[0.1] * 768)

    async def run():
        async with Database(database, 2) as db:
            graph.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN ('test-ws', 'other-ws')")
                with patch.object(openrouter, "_embed", embed):
                    first = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert first == {"workspace": "test-ws", "synced": 2, "unchanged": 0, "errors": 1, "not_shared": 1, "removed": 0}
                    status = {r: v[0] for r, v in google.writes}
                    assert status["'Document Index'!M2:O2"][0] == "synced" and status["'Document Index'!M2:O2"][2] == "1"
                    assert status["'Document Index'!M4:O4"] == ["error", "", ""]  # spreadsheets aren't indexed
                    assert not any("M5" in r for r, _ in google.writes)  # other workspace untouched
                    assert status["'Document Index'!M6:O6"] == ["not_shared", "", ""]
                    stored = await graph.documents.sheet_revisions("test-ws")
                    newer, older = stored["2"][0], stored["1"][0]
                    related = await graph.documents.related("test-ws", newer)
                    assert {"id": older, "relation": "supersedes", "direction": "outgoing"}.items() <= next(
                        r for r in related if r["relation"] == "supersedes").items()

                    google.downloads.clear()
                    second = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert second["unchanged"] == 2 and google.downloads == [] and embed.await_count == 2

                    google.values[1][11] = False  # untick row 1
                    third = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert third["removed"] == 1 and "1" not in await graph.documents.sheet_revisions("test-ws")
                    assert dict(google.writes)["'Document Index'!M2:O2"] == [["not_applicable", "", ""]]
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN ('test-ws', 'other-ws')")
                graph.configure(None)
    asyncio.run(run())


def test_restricted_login_can_write_and_search_agent_documents(database, monkeypatch):
    from horology_runtime.database import Database
    monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "test-ws")
    async def run():
        async with Database(database, 2) as db:
            graph.configure(db)
            try:
                with patch.object(openrouter, "_embed", AsyncMock(return_value=[0.2] * 768)):
                    doc = await graph.write_document("research", "Seat pricing research", "Seats beat usage.", "test-agent")
                    await graph.auto_link_similar_documents(doc["id"])
                    found = await graph.search_documents("pricing")
                assert found[0]["id"] == doc["id"] and found[0]["source"] == "agent"
                monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "other-ws")
                with pytest.raises(ValueError):
                    await graph.get_document(doc["id"])
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph.configure(None)
    asyncio.run(run())


def test_failed_embedding_stores_nothing_and_a_half_import_is_retried(database):
    from horology_runtime.database import Database
    files = {"fileAAAAAAAAAA": ("text/markdown", "3", "# Guide\nHow agents pick up work.")}
    google = FakeGoogle([HEADER, row("1", "Guide", "fileAAAAAAAAAA", True, doc_type="guide")], files)

    async def run():
        async with Database(database, 2) as db:
            graph.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(openrouter, "_embed", AsyncMock(side_effect=RuntimeError("401"))):
                    failed = await sync.sync_workspace(google, "test-ws", "sheet")
                assert failed["errors"] == 1 and await graph.documents.sheet_revisions("test-ws") == {}

                # A row stored by an older run without its embedding is not "unchanged".
                doc_id = await graph.documents.upsert_sheet_document("test-ws", "1", "fileAAAAAAAAAA", "u", "guide", "Guide", "x", "3")
                assert (await graph.documents.sheet_revisions("test-ws"))["1"] == (doc_id, None)
                with patch.object(openrouter, "_embed", AsyncMock(return_value=[0.3] * 768)):
                    fixed = await sync.sync_workspace(google, "test-ws", "sheet")
                assert fixed["synced"] == 1 and (await graph.documents.sheet_revisions("test-ws"))["1"] == (doc_id, "3")
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph.configure(None)
    asyncio.run(run())
