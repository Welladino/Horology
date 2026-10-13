"""
Unit tests for the document-graph MCP (mcp-servers/document-graph).

Mocked: a fake async database records SQL and returns scripted rows, and
OpenRouter is patched. No real DB, no real OpenRouter call, no Docker.
They verify our own logic (validation, workspace scoping, request shape),
not the live integration; see
docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md for why
hands-on verification against real systems remains the standing practice.
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

GRAPH_ROOT = Path(__file__).parent.parent.parent / "mcp-servers" / "document-graph"
sys.path.append(str(GRAPH_ROOT))  # append: the gateway also has a top-level server.py

from document_graph import graph  # noqa: E402
from document_graph.integrations.openrouter import client as openrouter  # noqa: E402

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, db):
        self.db = db
    async def __aenter__(self):
        return self
    async def __aexit__(self, *exc):
        return False
    async def execute(self, sql, params=()):
        self.db.executed.append((" ".join(sql.split()), params))
    async def fetchone(self):
        return self.db.one.pop(0) if self.db.one else None
    async def fetchall(self):
        return self.db.all.pop(0) if self.db.all else []


class FakeDatabase:
    def __init__(self, one=(), all=()):
        self.one, self.all, self.executed = list(one), list(all), []
    @asynccontextmanager
    async def transaction(self):
        conn = MagicMock()
        conn.cursor = lambda **kwargs: FakeCursor(self)
        yield conn


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "welladino")
    fake = FakeDatabase()
    graph.configure(fake)
    yield fake
    graph.configure(None)


def run(coro):
    return asyncio.run(coro)


class TestWriteDocument:
    def test_rejects_invalid_doc_type(self, db):
        with pytest.raises(ValueError, match="doc_type must be one of"):
            run(graph.write_document(doc_type="not_a_real_type", title="t", content="c", created_by_agent="a"))
        assert db.executed == []

    def test_accepts_each_document_index_type(self, db):
        assert {"plan", "guide", "research", "brand_guide", "recommendation"} <= set(graph.VALID_DOC_TYPES)
        for doc_type in graph.VALID_DOC_TYPES:
            db.one.append((1, NOW))
            assert run(graph.write_document(doc_type=doc_type, title="t", content="c", created_by_agent="a"))["id"] == 1

    def test_tags_agent_source_and_workspace(self, db):
        db.one.append((7, NOW))
        run(graph.write_document(doc_type="plan", title="t", content="c", created_by_agent="a"))
        sql, params = db.executed[-1]
        assert "'agent'" in sql and params[-1] == "welladino"

    def test_supersedes_must_be_in_workspace(self, db):
        db.one.append((0,))
        with pytest.raises(ValueError, match="No document with id 3"):
            run(graph.write_document(doc_type="plan", title="t", content="c", created_by_agent="a", supersedes_id=3))


class TestWorkspaceScoping:
    def test_reads_filter_by_current_workspace(self, db, monkeypatch):
        monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "job")
        db.one.append({"id": 1, "created_at": NOW})
        run(graph.get_document(1))
        run(graph.list_documents())
        run(graph.get_related_documents(1))
        run(graph.list_unembedded_documents())
        for sql, params in db.executed:
            assert "workspace = %s" in sql and "job" in params

    def test_get_document_outside_workspace_is_not_found(self, db):
        with pytest.raises(ValueError, match="No document with id 9"):
            run(graph.get_document(9))

    def test_link_requires_both_documents_in_workspace(self, db):
        db.one.append((1,))
        with pytest.raises(ValueError, match="Both documents must exist"):
            run(graph.link_documents(1, 2, "informed_by"))


class TestListDocuments:
    def test_rejects_invalid_doc_type_filter(self, db):
        with pytest.raises(ValueError, match="doc_type must be one of"):
            run(graph.list_documents(doc_type="bogus"))

    def test_clamps_limit_to_valid_range(self, db):
        run(graph.list_documents(limit=99999))
        assert db.executed[-1][1][-1] == 100


class TestSearchDocuments:
    def test_embeds_query_and_orders_by_distance_in_workspace(self, db):
        db.all.append([{"id": 4, "title": "Pricing", "created_at": NOW, "similarity": 0.91234}])
        with patch.object(openrouter, "_embed", AsyncMock(return_value=[0.5] * 768)) as embed:
            result = run(graph.search_documents("what have we done on pricing?", limit=50))
        embed.assert_awaited_once_with("what have we done on pricing?")
        sql, params = db.executed[-1]
        assert "<=> %s::vector" in sql and "d.workspace = %s" in sql
        assert params[1] == "welladino" and params[-1] == 20
        assert params[0].startswith("[0.5,") and result[0]["similarity"] == 0.9123

    def test_rejects_empty_query(self, db):
        with pytest.raises(ValueError, match="query must not be empty"):
            run(graph.search_documents("  "))


class TestEmbed:
    def test_sends_correct_openrouter_request_shape(self, monkeypatch):
        """Regression test for the real bug: the model's un-truncated output
        is 3072 dims (exceeds pgvector's 2000-dim HNSW limit), fixed by
        explicitly requesting 768 via `dimensions`."""
        monkeypatch.setattr(openrouter, "OPENROUTER_API_KEY", "sk-or-fake-key")
        response = MagicMock()
        response.json.return_value = {"data": [{"embedding": [0.1] * 768}]}
        with patch.object(openrouter.httpx.AsyncClient, "post", AsyncMock(return_value=response)) as post:
            result = run(openrouter._embed("some document text"))
        assert len(result) == 768
        _, kwargs = post.call_args
        assert kwargs["json"]["dimensions"] == 768
        assert kwargs["json"]["model"] == "google/gemini-embedding-001"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-or-fake-key"

    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.setattr(openrouter, "OPENROUTER_API_KEY", None)
        with pytest.raises(RuntimeError, match="operation_failed; request_id="):
            run(openrouter._embed("text"))


class TestGetRelatedDocuments:
    def test_returns_outgoing_and_incoming_edges(self, db):
        db.all.append([
            {"id": 5, "title": "Doc 5", "doc_type": "analysis", "relation": "related_to", "direction": "outgoing"},
            {"id": 2, "title": "Doc 2", "doc_type": "recommendation", "relation": "supersedes", "direction": "incoming"},
        ])
        result = run(graph.get_related_documents(document_id=1))
        assert [r["direction"] for r in result] == ["outgoing", "incoming"]

    def test_returns_empty_list_for_unlinked_document(self, db):
        assert run(graph.get_related_documents(document_id=1)) == []


class TestListUnembeddedDocuments:
    def test_returns_documents_missing_an_embedding(self, db):
        db.all.append([{"id": 3, "title": "Old doc", "doc_type": "report", "created_at": NOW}])
        result = run(graph.list_unembedded_documents())
        assert result[0]["id"] == 3 and result[0]["created_at"] == NOW.isoformat()


class TestAutoLinkSimilarDocuments:
    def test_raises_for_unknown_document(self, db):
        with pytest.raises(ValueError, match="No document with id"):
            run(graph.auto_link_similar_documents(document_id=999))

    def test_links_only_candidates_above_threshold(self, db):
        db.one += [("some document content",), (True,), (10,)]
        db.all.append([(101, 0.90), (102, 0.50)])
        with patch.object(openrouter, "_embed", AsyncMock()) as embed:
            result = run(graph.auto_link_similar_documents(document_id=1, threshold=0.85))
        embed.assert_not_awaited()
        assert result["candidates_checked"] == 2
        assert result["newly_linked"] == [{"document_id": 101, "similarity": 0.9}]
        assert any("d.workspace = %s" in sql for sql, _ in db.executed)

    def test_embeds_when_missing(self, db):
        db.one += [("content",), None]
        with patch.object(openrouter, "_embed", AsyncMock(return_value=[0.1] * 768)) as embed:
            run(graph.auto_link_similar_documents(document_id=1))
        embed.assert_awaited_once_with("content")
        assert any("INSERT INTO document_embeddings" in sql for sql, _ in db.executed)
