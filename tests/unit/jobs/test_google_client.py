"""The sync job's Sheets and Drive client (graph_sync/google.py), with httpx's fake transport.

Replies follow the shapes in Google's API reference (values.get, spreadsheets.get, files.get)."""
import asyncio
import json
import sys

import httpx
import pytest

from support.paths import SYNC_JOB

sys.path.append(str(SYNC_JOB))
from graph_sync import google  # noqa: E402

REAL_CLIENT = httpx.AsyncClient
SHEET = "1kObSheetId"


class Credentials:
    valid, token = True, "job-token"


def serve(monkeypatch, handler):
    """Route the client to handler(request); returns the requests seen."""
    seen = []

    def client(**options):
        assert options["follow_redirects"] is False and options["trust_env"] is False
        return REAL_CLIENT(transport=httpx.MockTransport(lambda r: seen.append(r) or handler(r)), **options)
    monkeypatch.setattr(httpx, "AsyncClient", client)
    return seen


def run(coroutine):
    return asyncio.run(coroutine)


def client():
    return google.GoogleClient(Credentials())


def test_sheet_rows_quote_the_tab_and_keep_values_typed(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={"range": "x", "values": [["Document ID", True], ["1", False]]}))
    assert run(client().sheet_rows(SHEET, "Bob's tab/2026")) == [["Document ID", True], ["1", False]]
    request = seen[0]
    # The A1 tab reference 'Bob''s tab/2026' as one escaped path segment, '/' included.
    assert request.url.raw_path.decode().startswith(f"/v4/spreadsheets/{SHEET}/values/%27Bob%27%27s%20tab%2F2026%27")
    assert request.url.params["valueRenderOption"] == "UNFORMATTED_VALUE"
    assert request.headers["Authorization"] == "Bearer job-token"


def test_an_empty_tab_has_no_rows(monkeypatch):
    serve(monkeypatch, lambda r: httpx.Response(200, json={"range": "x"}))  # Sheets omits "values" when empty
    assert run(client().sheet_rows(SHEET, "Empty")) == []


def test_writes_are_raw_and_nothing_is_sent_without_updates(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={}))
    run(client().write_cells(SHEET, []))
    assert seen == []
    run(client().write_cells(SHEET, [("'Document Index'!M2:O2", [["synced", "4", "7"]])]))
    body = json.loads(seen[0].content)
    assert seen[0].url.path.endswith("/values:batchUpdate") and body["valueInputOption"] == "RAW"
    assert body["data"] == [{"range": "'Document Index'!M2:O2", "values": [["synced", "4", "7"]]}]


def test_tabs_are_listed_added_and_replaced(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={"sheets": [{"properties": {"title": "Document Index"}},
                                                                             {"properties": {"title": "Entities"}}]}))
    assert run(client().tab_titles(SHEET)) == ["Document Index", "Entities"]
    run(client().add_tab(SHEET, "Entity types"))
    assert json.loads(seen[1].content) == {"requests": [{"addSheet": {"properties": {"title": "Entity types"}}}]}
    run(client().replace_tab(SHEET, "Entities", [["Entity ID"], ["1"]]))
    assert seen[2].url.raw_path.decode().endswith("/values/%27Entities%27:clear")  # cleared first, then written
    assert json.loads(seen[3].content)["data"] == [{"range": "'Entities'!A1", "values": [["Entity ID"], ["1"]]}]


def test_a_file_id_is_one_escaped_path_segment(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={"id": "x", "mimeType": "text/markdown", "version": "3"}))
    run(client().file_metadata("../../sheets/v4/x"))
    assert seen[0].url.raw_path.decode().startswith("/drive/v3/files/..%2F..%2Fsheets%2Fv4%2Fx")
    assert seen[0].url.params["supportsAllDrives"] == "true"


@pytest.mark.parametrize("status", [403, 404])
def test_an_unshared_file_raises_the_status_the_sync_turns_into_not_shared(monkeypatch, status):
    serve(monkeypatch, lambda r: httpx.Response(status, json={"error": {"code": status}}))
    with pytest.raises(httpx.HTTPStatusError) as raised:
        run(client().file_metadata("fileId123"))
    assert raised.value.response.status_code == status


def test_a_google_doc_is_exported_as_text(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, content="Plan ✓\n".encode()))
    text = run(client().file_text({"id": "doc1", "mimeType": google.GOOGLE_DOC}))
    assert text == "Plan ✓\n" and seen[0].url.path.endswith("/files/doc1/export")
    assert seen[0].url.params["mimeType"] == "text/plain"


@pytest.mark.parametrize("mime", google.TEXT_TYPES)
def test_markdown_and_text_are_downloaded(monkeypatch, mime):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, content=b"# Title\nBody"))
    assert run(client().file_text({"id": "md1", "mimeType": mime, "size": "12"})) == "# Title\nBody"
    assert seen[0].url.params["alt"] == "media"


def test_other_file_types_are_refused_without_a_download(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, content=b"x"))
    with pytest.raises(ValueError, match="Unsupported file type"):
        run(client().file_text({"id": "s1", "mimeType": "application/vnd.google-apps.spreadsheet"}))
    assert seen == []


def test_a_file_over_the_size_limit_in_its_metadata_is_refused_without_a_download(monkeypatch):
    seen = serve(monkeypatch, lambda r: httpx.Response(200, content=b"x"))
    with pytest.raises(ValueError, match="too large"):
        run(client().file_text({"id": "big", "mimeType": "text/plain", "size": str(google.MAX_FILE_BYTES + 1)}))
    assert seen == []


@pytest.mark.parametrize("meta", [{"id": "doc1", "mimeType": google.GOOGLE_DOC},  # Docs report no size
                                  {"id": "md1", "mimeType": "text/markdown", "size": "10"}])  # size understated
def test_an_oversized_download_is_refused_before_it_has_all_arrived(monkeypatch, meta):
    sent = []

    async def huge():  # 50 MB in 100 KB chunks, unless the reader stops
        for _ in range(500):
            sent.append(1)
            yield b"a" * 100_000
    serve(monkeypatch, lambda r: httpx.Response(200, content=huge()))
    with pytest.raises(ValueError, match="too large"):
        run(client().file_text(meta))
    assert len(sent) <= google.MAX_FILE_BYTES // 100_000 + 1  # stopped at about 2 MB, not 50 MB


def test_invalid_utf8_is_replaced_not_fatal(monkeypatch):
    serve(monkeypatch, lambda r: httpx.Response(200, content=b"ok \xff\xfe end"))
    assert run(client().file_text({"id": "t", "mimeType": "text/plain", "size": "10"})) == "ok �� end"


def test_an_expired_token_is_refreshed_first(monkeypatch):
    class Expired:
        valid, token, refreshed = False, "new-token", 0

        def refresh(self, request):
            Expired.refreshed += 1
    seen = serve(monkeypatch, lambda r: httpx.Response(200, json={"values": []}))
    run(google.GoogleClient(Expired()).sheet_rows(SHEET, "Tab"))
    assert Expired.refreshed == 1 and seen[0].headers["Authorization"] == "Bearer new-token"
