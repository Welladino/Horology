"""
Unit tests for the document-graph MCP (mcp-servers/document-graph).

Mocked: a fake async database records SQL and returns scripted rows, and
OpenRouter is patched. No real DB, no real OpenRouter call, no Docker.
They verify our own logic (validation, workspace scoping, request shape),
not the live integration; see
docs/planning/notes/2026-08-06_document-graph-v1_note.md for why
hands-on verification against real systems remains the standing practice.
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from support.paths import DOCUMENT_GRAPH as GRAPH_ROOT  # noqa: E402
sys.path.append(str(GRAPH_ROOT))  # append: the gateway also has a top-level server.py

from document_graph import graph  # noqa: E402
import graph_core  # noqa: E402
from graph_core.documents import service as documents  # noqa: E402
from graph_core.ai import embeddings  # noqa: E402
from graph_core.ai.openrouter import embeddings as openrouter_embeddings  # noqa: E402

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
    async def executemany(self, sql, rows):
        self.db.executed.append((" ".join(sql.split()), list(rows)))
    async def fetchone(self):
        return self.db.one.pop(0) if self.db.one else None
    async def fetchall(self):
        return self.db.all.pop(0) if self.db.all else []
    def nextset(self):
        return True


class FakeDatabase:
    def __init__(self, one=(), all=()):
        self.one, self.all, self.executed = list(one), list(all), []
    @asynccontextmanager
    async def transaction(self):
        conn = MagicMock()
        conn.cursor = lambda **kwargs: FakeCursor(self)
        yield conn

    connection = transaction


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "welladino")
    fake = FakeDatabase()
    graph_core.configure(fake)
    yield fake
    graph_core.configure(None)


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

    def test_a_document_over_the_section_limit_is_not_saved(self, db):
        long = "\n\n".join(("Paragraph about the market. " * 70) for _ in range(40))
        reply = run(graph.write_document(doc_type="plan", title="t", content=long, created_by_agent="a"))
        assert reply["saved"] is False and reply["reason"] == "too_long" and reply["sections"] > reply["limit"] == 30
        assert db.executed == []

    def test_tags_agent_source_and_workspace(self, db):
        db.one.append((7, NOW))
        run(graph.write_document(doc_type="plan", title="t", content="c", created_by_agent="a"))
        sql, params = db.executed[-1]
        assert "'agent'" in sql and params[5] == "welladino" and params[-2:] == (None, None)

    def test_stores_domain_and_pipeline_id_in_normal_form(self, db):
        db.one.append((7, NOW))
        run(graph.write_document(doc_type="plan", title="t", content="c", created_by_agent="a",
                                 domain="Article Aggregator", pipeline_id=12.0))
        assert db.executed[-1][1][-2:] == ("article-aggregator", "12")

    def test_rejects_a_non_numeric_pipeline_id_before_writing(self, db):
        with pytest.raises(ValueError, match="Pipeline ID must be a number"):
            run(graph.write_document(doc_type="plan", title="t", content="c", created_by_agent="a", pipeline_id="PL-7"))
        assert db.executed == []

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
        db.one.append((False, None))  # (both exist, new link id)
        with pytest.raises(ValueError, match="Both documents must exist"):
            run(graph.link_documents(1, 2, "informed_by"))


class TestDomainFilter:
    def test_list_and_search_filter_by_normalised_domain(self, db):
        run(graph.list_documents(domain="Newsletter"))
        assert db.executed[-1][1][3:5] == ("newsletter", "newsletter")
        with patch.object(embeddings, "embed", AsyncMock(return_value=[0.5] * 768)):
            run(graph.search_documents("growth", domain="newsletter"))
        assert db.executed[-1][1][2:4] == ("newsletter", "newsletter")


class TestListDocuments:
    def test_rejects_invalid_doc_type_filter(self, db):
        with pytest.raises(ValueError, match="doc_type must be one of"):
            run(graph.list_documents(doc_type="bogus"))

    def test_clamps_limit_to_valid_range(self, db):
        run(graph.list_documents(limit=99999))
        assert db.executed[-1][1][-1] == 100


def section(doc_id, index, similarity, title="Pricing"):
    return {"id": doc_id, "doc_type": "research", "title": title, "created_by_agent": "a", "supersedes_id": None,
            "source": "sheet", "drive_url": None, "created_at": NOW, "chunk_index": index,
            "passage": f"passage {doc_id}.{index}", "similarity": similarity}


class TestSearchDocuments:
    def test_searches_sections_in_workspace_and_groups_by_document(self, db):
        db.all.append([section(4, 2, 0.91234), section(7, 0, 0.88), section(4, 5, 0.85), section(4, 1, 0.80), section(9, 3, 0.70)])
        with patch.object(embeddings, "embed", AsyncMock(return_value=[0.5] * 768)) as embed:
            result = run(graph.search_documents("what have we done on pricing?", limit=2))
        embed.assert_awaited_once_with("what have we done on pricing?")
        sql, params = db.executed[-1]
        assert "FROM document_chunks c JOIN documents d" in sql and "d.workspace = %s" in sql
        assert params[1] == "welladino" and params[-1] == 16
        assert [r["id"] for r in result] == [4, 7]  # best section decides the order; doc 9 is past the limit
        assert result[0]["similarity"] == 0.9123 and result[0]["created_at"] == NOW.isoformat()
        assert result[0]["passages"] == [{"section": 2, "similarity": 0.9123, "text": "passage 4.2"},
                                         {"section": 5, "similarity": 0.85, "text": "passage 4.5"}]

    def test_clamps_limit_and_passages(self, db):
        db.all.append([section(4, i, 0.9 - i / 100) for i in range(5)])
        with patch.object(embeddings, "embed", AsyncMock(return_value=[0.5] * 768)):
            result = run(graph.search_documents("pricing", limit=50, passages=9))
        assert db.executed[-1][1][-1] == 160 and len(result[0]["passages"]) == 3

    def test_rejects_empty_query(self, db):
        with pytest.raises(ValueError, match="query must not be empty"):
            run(graph.search_documents("  "))


class TestEmbed:
    def test_sends_correct_openrouter_request_shape(self, monkeypatch):
        """Regression test for the real bug: the model's un-truncated output
        is 3072 dims (exceeds pgvector's 2000-dim HNSW limit), fixed by
        explicitly requesting 768 via `dimensions`."""
        monkeypatch.setattr(openrouter_embeddings, "OPENROUTER_API_KEY", "sk-or-fake-key")
        response = MagicMock()
        response.json.return_value = {"data": [{"index": 0, "embedding": [0.1] * 768}]}
        with patch.object(openrouter_embeddings.httpx.AsyncClient, "post", AsyncMock(return_value=response)) as post:
            result = run(embeddings.embed("some document text"))
        assert len(result) == 768
        _, kwargs = post.call_args
        assert kwargs["json"]["input"] == ["some document text"]
        assert kwargs["json"]["dimensions"] == 768
        assert kwargs["json"]["model"] == "google/gemini-embedding-001"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-or-fake-key"

    def test_batches_sections_and_keeps_input_order(self, monkeypatch):
        monkeypatch.setattr(openrouter_embeddings, "OPENROUTER_API_KEY", "sk-or-fake-key")
        def reply(*args, json, **kwargs):
            response = MagicMock()
            # Answer out of order, as the API may; vectors carry their input text's length.
            response.json.return_value = {"data": [{"index": i, "embedding": [float(len(json["input"][i]))]}
                                                   for i in reversed(range(len(json["input"])))]}
            return response
        texts = ["x" * n for n in range(1, 41)]
        with patch.object(openrouter_embeddings.httpx.AsyncClient, "post", AsyncMock(side_effect=reply)) as post:
            vectors = run(embeddings.embed_many(texts))
        assert post.await_count == 2  # 32 + 8
        assert [v[0] for v in vectors] == [float(n) for n in range(1, 41)]

    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.setattr(openrouter_embeddings, "OPENROUTER_API_KEY", None)
        with pytest.raises(RuntimeError, match="operation_failed; request_id="):
            run(embeddings.embed("text"))


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
        db.one.append(("A plan", "some document content", True))  # (title, content, has sections)
        db.all += [[(101, 0.90), (102, 0.50)], [(101,)]]  # similar documents; the links newly added
        with patch.object(embeddings, "embed_many", AsyncMock()) as embed:
            result = run(graph.auto_link_similar_documents(document_id=1, threshold=0.85))
        embed.assert_not_awaited()
        assert result["candidates_checked"] == 2
        assert result["newly_linked"] == [{"document_id": 101, "similarity": 0.9}]
        assert any("d.workspace = %s" in sql for sql, _ in db.executed)

    def test_embeds_sections_when_missing(self, db):
        from graph_core.sections import repository as section_repository
        db.one.append(("A plan", "content", False))
        with patch.object(embeddings, "embed_many", AsyncMock(return_value=[[0.1] * 768])) as embed, \
                patch.object(section_repository, "AsyncClientCursor", lambda conn: FakeCursor(db)):
            run(graph.auto_link_similar_documents(document_id=1))
        embed.assert_awaited_once_with(["A plan\n\ncontent"])
        sql, params = next((sql, params) for sql, params in db.executed if "INSERT INTO document_chunks" in sql)
        # One round trip: the document vector, the old sections' removal and the new sections together
        assert "INSERT INTO document_embeddings" in sql and "DELETE FROM document_chunks" in sql
        assert params[3:6] == [1, 0, "content"]


class TestSyncGraph:
    @pytest.fixture(autouse=True)
    def client_cursor(self, db):
        """Run requests use a client-side cursor (one round trip); the fake stands in for it."""
        from graph_core.runs import repository
        with patch.object(repository, "AsyncClientCursor", lambda conn: FakeCursor(db)):
            yield

    def test_refuses_without_a_configured_job(self, db, monkeypatch):
        db.one.append((None, None, 1))  # (running mode, cooldown seconds, claimed)
        monkeypatch.delenv("GRAPH_SYNC_JOB", raising=False)
        with pytest.raises(ValueError, match="not configured"):
            run(graph.sync_graph())

    def test_starts_the_job_for_the_callers_workspace_only(self, db, monkeypatch):
        from graph_core.runs import cloud_run
        monkeypatch.setenv("GRAPH_SYNC_JOB", "projects/horology-dev/locations/us-central1/jobs/document-graph-sync")
        monkeypatch.setenv("DOCUMENT_GRAPH_WORKSPACE", "job")
        db.one.append((None, None, 1))
        response = MagicMock()
        response.json.return_value = {"name": "operations/123"}
        with patch.object(cloud_run, "_token", AsyncMock(return_value="token")), \
                patch.object(cloud_run.httpx.AsyncClient, "post", AsyncMock(return_value=response)) as post:
            result = run(graph.sync_graph())
        url = post.call_args.args[0]
        body = post.call_args.kwargs["json"]
        assert url == "https://run.googleapis.com/v2/projects/horology-dev/locations/us-central1/jobs/document-graph-sync:run"
        assert body["overrides"]["containerOverrides"][0]["env"] == [{"name": "GRAPH_SYNC_WORKSPACE", "value": "job"},
                                                                     {"name": "GRAPH_SYNC_MODE", "value": "sync"},
                                                                     {"name": "GRAPH_SYNC_CHAIN", "value": "1"},
                                                                     {"name": "GRAPH_RUN_TOKEN", "value": ANY}]
        assert result == {"started": True, "workspace": "job", "operation": "operations/123"}

    def test_rebuild_topics_starts_the_job_in_topics_mode(self, db, monkeypatch):
        from graph_core.runs import cloud_run
        monkeypatch.setenv("GRAPH_SYNC_JOB", "projects/horology-dev/locations/us-central1/jobs/document-graph-sync")
        db.one.append((None, None, 1))
        response = MagicMock()
        response.json.return_value = {"name": "operations/456"}
        with patch.object(cloud_run, "_token", AsyncMock(return_value="token")), \
                patch.object(cloud_run.httpx.AsyncClient, "post", AsyncMock(return_value=response)) as post:
            result = run(graph.rebuild_topics())
        env = post.call_args.kwargs["json"]["overrides"]["containerOverrides"][0]["env"]
        assert {"name": "GRAPH_SYNC_MODE", "value": "topics"} in env and result["started"] is True

    def test_unknown_mode_is_refused(self, db, monkeypatch):
        from graph_core.runs import cloud_run
        with pytest.raises(ValueError, match="mode must be one of"):
            run(cloud_run.start("welladino", "delete-everything"))

    def test_not_started_while_a_run_is_in_progress(self, db, monkeypatch):
        from graph_core.runs import cloud_run
        db.one.append(("sync", None, 0))  # a sync run holds the workspace
        with patch.object(cloud_run, "start", AsyncMock()) as start:
            result = run(graph.rebuild_topics())
        assert result["started"] is False and result["reason"] == "already_running" and result["running"] == "sync"
        start.assert_not_awaited()

    def test_not_started_within_the_cooldown(self, db, monkeypatch):
        from graph_core.runs import cloud_run
        db.one.append((None, 120, 0))  # nothing running; asked 3 minutes ago
        with patch.object(cloud_run, "start", AsyncMock()) as start:
            result = run(graph.sync_graph())
        assert result == {"workspace": "welladino", "started": False, "reason": "cooldown", "retry_after_seconds": 120}
        start.assert_not_awaited()

    def test_a_failed_start_clears_the_request_so_the_agent_can_retry(self, db, monkeypatch):
        monkeypatch.delenv("GRAPH_SYNC_JOB", raising=False)
        db.one.append((None, None, 1))
        with pytest.raises(ValueError):
            run(graph.sync_graph())
        assert "running_since = NULL" in db.executed[-1][0] and "requested_at = NULL" in db.executed[-1][0]

    def test_rejects_a_malformed_job_name(self, db, monkeypatch):
        monkeypatch.setenv("GRAPH_SYNC_JOB", "https://evil.example/jobs/x")
        db.one.append((None, None, 1))
        with pytest.raises(ValueError, match="not configured"):
            run(graph.sync_graph())
