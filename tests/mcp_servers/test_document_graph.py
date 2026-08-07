"""
Unit tests for mcp-servers/document-graph/server.py.

Covers:
- write_document rejects an invalid doc_type before touching the DB
- link_documents / auto_link_similar_documents reject/accept threshold
  and similarity math correctly, without a real database
- _embed sends the exact request shape OpenRouter's /v1/embeddings
  endpoint expects, including the 768-dim `dimensions` param (this
  is the exact parameter that fixed a real bug found during manual
  testing - see docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md)

These are mocked (no real DB, no real OpenRouter call, no Docker) -
they verify our own logic, not the live integration. The two real bugs
found this project (wrong embedding dimension, HNSW dimension limit)
were caught by live testing against the real API, not by unit tests -
mocks would not have caught either. See that note for why "verify
hands-on" remains the standing practice for anything touching a real
external system, even with this suite in place.

Source under test: mcp-servers/document-graph/server.py
"""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SERVER_PATH = Path(__file__).parent.parent.parent / "mcp-servers" / "document-graph" / "server.py"


def _fake_conn():
    """server.py uses `with _connect() as conn, conn.cursor() as cur:` -
    both the connection AND the cursor are used as their own context
    managers (not `conn.cursor().__enter__()` nested inside), matching
    real psycopg2 behavior. Returns (conn, cursor) mocks wired up that way."""
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


@pytest.fixture
def server_module(monkeypatch):
    """Import server.py fresh with fake required env vars set, so module-level
    validation (DATABASE_URL_POOLED / OPENROUTER_API_KEY presence checks)
    passes without real credentials."""
    monkeypatch.setenv("DATABASE_URL_POOLED", "postgresql://fake:fake@localhost/fake")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-fake-key")

    spec = importlib.util.spec_from_file_location("document_graph_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["document_graph_server"] = module
    spec.loader.exec_module(module)
    yield module
    del sys.modules["document_graph_server"]


class TestWriteDocument:
    def test_rejects_invalid_doc_type(self, server_module):
        with pytest.raises(ValueError, match="doc_type must be one of"):
            server_module.write_document(
                doc_type="not_a_real_type",
                title="t",
                content="c",
                created_by_agent="test-agent",
            )

    def test_accepts_each_valid_doc_type(self, server_module):
        for doc_type in server_module.VALID_DOC_TYPES:
            fake_conn, fake_cursor = _fake_conn()
            fake_cursor.fetchone.return_value = (1, MagicMock(isoformat=lambda: "2026-08-06T00:00:00"))
            with patch.object(server_module, "_connect", return_value=fake_conn):
                result = server_module.write_document(
                    doc_type=doc_type,
                    title="t",
                    content="c",
                    created_by_agent="test-agent",
                )
            assert result["id"] == 1


class TestListDocuments:
    def test_rejects_invalid_doc_type_filter(self, server_module):
        with pytest.raises(ValueError, match="doc_type must be one of"):
            server_module.list_documents(doc_type="bogus")

    def test_clamps_limit_to_valid_range(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchall.return_value = []
        with patch.object(server_module, "_connect", return_value=fake_conn):
            server_module.list_documents(limit=99999)
        # last positional bind param should be clamped to 100, not 99999
        call_args = fake_cursor.execute.call_args
        assert call_args[0][1][-1] == 100


class TestEmbed:
    def test_sends_correct_openrouter_request_shape(self, server_module):
        """Regression test for the real bug: the model's un-truncated output
        is 3072 dims (exceeds pgvector's 2000-dim HNSW limit), fixed by
        explicitly requesting 768 via `dimensions`. If this param is ever
        dropped, embeddings would silently come back at 3072 dims again."""
        fake_response = MagicMock()
        fake_response.json.return_value = {"data": [{"embedding": [0.1] * 768}]}
        fake_response.raise_for_status.return_value = None

        with patch.object(server_module.httpx, "post", return_value=fake_response) as mock_post:
            result = server_module._embed("some document text")

        assert len(result) == 768
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["dimensions"] == 768
        assert kwargs["json"]["model"] == "google/gemini-embedding-001"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-or-fake-key"

    def test_raises_without_api_key(self, server_module, monkeypatch):
        monkeypatch.setattr(server_module, "OPENROUTER_API_KEY", None)
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            server_module._embed("text")


class TestGetRelatedDocuments:
    def test_returns_outgoing_and_incoming_edges(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchall.return_value = [
            {"id": 5, "title": "Doc 5", "doc_type": "analysis", "relation": "related_to", "direction": "outgoing"},
            {"id": 2, "title": "Doc 2", "doc_type": "recommendation", "relation": "supersedes", "direction": "incoming"},
        ]
        with patch.object(server_module, "_connect", return_value=fake_conn):
            result = server_module.get_related_documents(document_id=1)

        assert len(result) == 2
        assert result[0]["direction"] == "outgoing"
        assert result[1]["direction"] == "incoming"

    def test_returns_empty_list_for_unlinked_document(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchall.return_value = []
        with patch.object(server_module, "_connect", return_value=fake_conn):
            result = server_module.get_related_documents(document_id=1)
        assert result == []


class TestListUnembeddedDocuments:
    def test_returns_documents_missing_an_embedding(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchall.return_value = [
            {"id": 3, "title": "Old doc", "doc_type": "report",
             "created_at": MagicMock(isoformat=lambda: "2026-08-01T00:00:00")},
        ]
        with patch.object(server_module, "_connect", return_value=fake_conn):
            result = server_module.list_unembedded_documents()

        assert len(result) == 1
        assert result[0]["id"] == 3
        assert result[0]["created_at"] == "2026-08-01T00:00:00"

    def test_returns_empty_list_when_nothing_missing(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchall.return_value = []
        with patch.object(server_module, "_connect", return_value=fake_conn):
            result = server_module.list_unembedded_documents()
        assert result == []


class TestAutoLinkSimilarDocuments:
    def test_raises_for_unknown_document(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchone.return_value = None
        with patch.object(server_module, "_connect", return_value=fake_conn):
            with pytest.raises(ValueError, match="No document with id"):
                server_module.auto_link_similar_documents(document_id=999)

    def test_links_only_candidates_above_threshold(self, server_module):
        fake_conn, fake_cursor = _fake_conn()
        fake_cursor.fetchone.side_effect = [
            ("some document content",),  # content lookup
            (1,),  # embedding already exists (skip _embed call)
            (10,),  # link insert for doc above threshold -> returns id
            None,  # link insert for doc below threshold -> filtered before insert, not reached
        ]
        fake_cursor.fetchall.return_value = [
            (101, 0.90),  # above 0.85 threshold -> should link
            (102, 0.50),  # below threshold -> should NOT link
        ]
        with patch.object(server_module, "_connect", return_value=fake_conn):
            result = server_module.auto_link_similar_documents(document_id=1, threshold=0.85)

        assert result["candidates_checked"] == 2
        assert len(result["newly_linked"]) == 1
        assert result["newly_linked"][0]["document_id"] == 101
        assert result["newly_linked"][0]["similarity"] == 0.9
