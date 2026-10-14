"""Document Index -> graph sync job, end to end.

Runs the real sync against a disposable migrated Postgres as the restricted
horology_graph login (GRAPH_TEST_RUNTIME_URL), with a fake Google client and a
fake embedding, so it also proves that login's grants are enough.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, patch

import graph_core
from graph_core.ai import embeddings
from graph_core.documents import service as documents
from graph_core.documents.repository import DocumentRepository
from graph_core.sections import service as sections

from support.document_index import FIELD_HEADER, HEADER, field_row, row
from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import index, sync  # noqa: E402


class FakeGoogle:
    def __init__(self, values, files):
        self.values, self.files, self.writes, self.downloads, self.calls = values, files, [], [], []
    async def sheet_rows(self, spreadsheet_id, tab):
        return self.values
    async def write_cells(self, spreadsheet_id, updates):
        self.calls.append(list(updates))
        self.writes += updates  # every write, in order; dict(self.writes) gives the latest per range
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


def test_sync_imports_skips_unchanged_removes_and_writes_status(database):
    from horology_runtime.database import Database
    files = {"fileAAAAAAAAAA": ("text/markdown", "1", "# Pricing plan\nCharge per seat."),
             "fileBBBBBBBBBB": ("text/markdown", "4", "# Pricing v2\nCharge per workspace."),
             "fileCCCCCCCCCC": ("application/vnd.google-apps.spreadsheet", "1", ""),
             "fileDDDDDDDDDD": ("text/markdown", "1", "\n\n".join(("Market background. " * 100) for _ in range(40)))}
    google = FakeGoogle([HEADER,
                         row("1", "Pricing plan", "fileAAAAAAAAAA", True),
                         row("2", "Pricing v2", "fileBBBBBBBBBB", True, supersedes="1"),
                         row("3", "A register", "fileCCCCCCCCCC", True, doc_type="guide"),
                         row("4", "Other workspace", "fileAAAAAAAAAA", True, workspace="other-ws"),
                         row("5", "Not shared", "fileZZZZZZZZZZ", True),
                         row("6", "Too long", "fileDDDDDDDDDD", True)], files)
    embed = AsyncMock(side_effect=lambda texts: [[0.1] * 768 for _ in texts])

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN ('test-ws', 'other-ws')")
                with patch.object(embeddings, "embed_many", embed):
                    first = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert first == {"workspace": "test-ws", "synced": 2, "unchanged": 0, "errors": 1, "not_shared": 1, "too_long": 1,
                                     "removed": 0, "fields_updated": 0, "deferred": 0}
                    status = {r: v[0] for r, v in google.writes}
                    assert status["'Document Index'!M2:O2"][0] == "synced" and status["'Document Index'!M2:O2"][2] == "1"
                    assert status["'Document Index'!M4:O4"] == ["error", "", ""]  # spreadsheets aren't indexed
                    assert not any("M5" in r for r, _ in google.writes)  # other workspace untouched
                    assert status["'Document Index'!M6:O6"] == ["not_shared", "", ""]
                    assert status["'Document Index'!M7:O7"] == ["too_long", "", ""]
                    assert "6" not in await documents.sheet_revisions("test-ws")  # nothing stored
                    assert all(len(texts) <= 32 and "Market background" not in texts[0] for texts in
                               (call.args[0] for call in embed.await_args_list))  # nor embedded
                    stored = await documents.sheet_revisions("test-ws")
                    newer, older = stored["2"][0], stored["1"][0]
                    related = await documents.related("test-ws", newer)
                    assert {"id": older, "relation": "supersedes", "direction": "outgoing"}.items() <= next(
                        r for r in related if r["relation"] == "supersedes").items()

                    google.downloads.clear()
                    second = await sync.sync_workspace(google, "test-ws", "sheet")
                    # A too-long file is re-read each sync (free, no AI calls) so a shortened version is picked up.
                    assert second["unchanged"] == 2 and google.downloads == ["fileDDDDDDDDDD"] and embed.await_count == 2

                    google.values[1][11] = False  # untick row 1
                    third = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert third["removed"] == 1 and "1" not in await documents.sheet_revisions("test-ws")
                    assert dict(google.writes)["'Document Index'!M2:O2"] == [["not_applicable", "", ""]]
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN ('test-ws', 'other-ws')")
                graph_core.configure(None)
    asyncio.run(run())


def test_restricted_login_can_write_and_search_agent_documents(database):
    from horology_runtime.database import Database
    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                with patch.object(embeddings, "embed", AsyncMock(return_value=[0.2] * 768)), \
                        patch.object(embeddings, "embed_many", AsyncMock(side_effect=lambda texts: [[0.2] * 768 for _ in texts])):
                    doc_id, _ = await documents.write_agent_document("test-ws", "research", "Seat pricing research", "Seats beat usage.", "test-agent")
                    await documents.embed_if_needed("test-ws", doc_id)
                    await documents.link_similar("test-ws", doc_id)
                    found = await sections.search_passages("test-ws", "pricing", 5, 2)
                assert found[0]["id"] == doc_id and found[0]["source"] == "agent"
                assert found[0]["passages"][0]["text"] == "Seats beat usage."
                assert await documents.get("other-ws", doc_id) is None
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())


def test_failed_embedding_stores_nothing_and_a_half_import_is_retried(database):
    from horology_runtime.database import Database
    files = {"fileAAAAAAAAAA": ("text/markdown", "3", "# Guide\nHow agents pick up work.")}
    google = FakeGoogle([HEADER, row("1", "Guide", "fileAAAAAAAAAA", True, doc_type="guide")], files)

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(embeddings, "embed_many", AsyncMock(side_effect=RuntimeError("401"))):
                    failed = await sync.sync_workspace(google, "test-ws", "sheet")
                assert failed["errors"] == 1 and await documents.sheet_revisions("test-ws") == {}

                # A row stored by an older run without its embedding is not "unchanged".
                doc_id = await DocumentRepository(db).upsert_sheet_document("test-ws", "1", "fileAAAAAAAAAA", "u", "guide", "Guide", "x", "3")
                assert (await documents.sheet_revisions("test-ws"))["1"] == (doc_id, None)
                with patch.object(embeddings, "embed_many", AsyncMock(side_effect=lambda texts: [[0.3] * 768 for _ in texts])):
                    fixed = await sync.sync_workspace(google, "test-ws", "sheet")
                assert fixed["synced"] == 1 and (await documents.sheet_revisions("test-ws"))["1"] == (doc_id, "3")
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())


def test_long_document_is_searchable_past_the_old_cutoff(database):
    """A detail far down a long document is found, and returned as the passage."""
    from horology_runtime.database import Database
    filler = "\n\n".join("Background paragraph about the market and our customers." * 5 for _ in range(60))
    text = "# Long plan\n\n" + filler + "\n\n## Pricing\n\nWe will charge per seat, billed yearly."
    assert text.index("charge per seat") > 8000
    google = FakeGoogle([HEADER, row("1", "Long plan", "fileAAAAAAAAAA", True)], {"fileAAAAAAAAAA": ("text/markdown", "1", text)})

    def fake_vector(text):  # sections about seat pricing point one way, everything else another
        return [1.0, 0.0] + [0.0] * 766 if "per seat" in text else [0.0, 1.0] + [0.0] * 766

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(embeddings, "embed_many", AsyncMock(side_effect=lambda texts: [fake_vector(t) for t in texts])):
                    assert (await sync.sync_workspace(google, "test-ws", "sheet"))["synced"] == 1
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("SELECT count(*), max(length(c.content)) FROM document_chunks c JOIN documents d ON d.id = c.document_id WHERE d.workspace = 'test-ws'")
                    count, longest = await cur.fetchone()
                assert count > 5 and longest <= 2000
                with patch.object(embeddings, "embed", AsyncMock(return_value=fake_vector("per seat"))):
                    found = await sections.search_passages("test-ws", "how will we price it?", 5, 1)
                assert found[0]["title"] == "Long plan" and "charge per seat" in found[0]["passages"][0]["text"]
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())


def test_fields_are_stamped_and_refreshed_without_re_embedding(database):
    from horology_runtime.database import Database
    files = {"fileAAAAAAAAAA": ("text/markdown", "1", "# Launch plan\nGrow to 500 subscribers.")}
    google = FakeGoogle([FIELD_HEADER, field_row("1", "fileAAAAAAAAAA", "Newsletter", "Daily Brief", 12)], files)
    embed = AsyncMock(side_effect=lambda texts: [[0.4] * 768 for _ in texts])

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(embeddings, "embed_many", embed):
                    await sync.sync_workspace(google, "test-ws", "sheet")
                    doc_id = (await documents.sheet_revisions("test-ws"))["1"][0]
                    stored = await documents.get("test-ws", doc_id)
                    assert (stored["domain"], stored["business_entity"], stored["pipeline_id"]) == ("newsletter", "Daily Brief", "12")

                    # A sheet-only edit (no new Drive revision) reaches the graph without embedding again.
                    google.values[1][-3:] = ["Ecommerce", "", "PL-x"]
                    second = await sync.sync_workspace(google, "test-ws", "sheet")
                    assert second["unchanged"] == 1 and second["fields_updated"] == 1 and embed.await_count == 1
                    stored = await documents.get("test-ws", doc_id)
                    assert (stored["domain"], stored["business_entity"], stored["pipeline_id"]) == ("ecommerce", None, None)
                    assert (await sync.sync_workspace(google, "test-ws", "sheet"))["fields_updated"] == 0
                    assert [r["id"] for r in await documents.list_recent("test-ws", None, 10, "ECOMMERCE")] == [doc_id]
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())


def test_statuses_are_written_in_batches_as_rows_finish(database):
    """A crash mid-run loses at most the last batch of statuses; the work itself is already saved."""
    from horology_runtime.database import Database
    files = {f"file{n:010d}": ("text/markdown", "1", f"# Plan {n}\nDetail {n}.") for n in range(23)}
    google = FakeGoogle([HEADER] + [row(str(n), f"Plan {n}", f"file{n:010d}", True) for n in range(23)]
                        + [row("99", "Left out", "file0000000000", False)], files)

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(embeddings, "embed_many", AsyncMock(side_effect=lambda texts: [[0.1] * 768 for _ in texts])):
                    assert (await sync.sync_workspace(google, "test-ws", "sheet"))["synced"] == 23
                # 10 + 10 during the run; the last 3 plus the excluded row at the end
                assert [len(call) for call in google.calls] == [10, 10, 4]
                assert google.calls[-1][-1][1] == [["not_applicable", "", ""]]

                google.calls.clear()
                ticks = iter(range(0, 10_000, 31))  # every row "takes" 31 s: a write after each row
                with patch.object(sync, "clock", lambda: next(ticks)):
                    await sync.sync_workspace(google, "test-ws", "sheet")
                assert [len(call) for call in google.calls] == [1] * 23 + [1]  # then the excluded row
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())


def test_a_run_stops_at_its_cap_and_leaves_the_rest_untouched(database):
    """Only rows that needed work count; deferred rows keep their copy and their sheet status."""
    from horology_runtime.database import Database
    files = {f"file{n:010d}": ("text/markdown", "1", f"# Plan {n}\nDetail {n}.") for n in range(7)}
    google = FakeGoogle([HEADER] + [row(str(n), f"Plan {n}", f"file{n:010d}", True) for n in range(7)], files)

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                with patch.object(embeddings, "embed_many", AsyncMock(side_effect=lambda texts: [[0.1] * 768 for _ in texts])):
                    assert (await sync.sync_workspace(google, "test-ws", "sheet"))["synced"] == 7
                    for n in range(7):  # every file edited
                        files[f"file{n:010d}"] = ("text/markdown", "2", f"# Plan {n}\nDetail {n}, revised.")
                    google.writes.clear()
                    capped = await sync.sync_workspace(google, "test-ws", "sheet", limit=3)
                    assert (capped["synced"], capped["deferred"], capped["removed"]) == (3, 4, 0)
                    assert len(await documents.sheet_revisions("test-ws")) == 7  # deferred rows kept
                    assert sorted(r for r, _ in google.writes) == [f"'Document Index'!M{n}:O{n}" for n in (2, 3, 4)]
                    rest = await sync.sync_workspace(google, "test-ws", "sheet", limit=3)
                    assert (rest["unchanged"], rest["synced"], rest["deferred"]) == (3, 3, 1)  # unchanged rows don't count
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = 'test-ws'")
                graph_core.configure(None)
    asyncio.run(run())
