"""Topics end to end against a disposable migrated Postgres, as the restricted horology_graph login.

Embeddings are synthetic: two themes point in two directions, with a little
spread so sections differ. The LLM is faked.
"""
import asyncio
import math
import os
from unittest.mock import AsyncMock, patch

import pytest

import graph_core
from graph_core.documents import service as documents
from graph_core.sections import service as sections
from graph_core.topics import naming, service as topics

WS = "topics-test"


def vector(theme, spread):
    v = [0.0] * 768
    v[theme] = 1.0
    v[100 + spread] = 0.25
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


async def add(theme, spread, title, doc_type="research", domain=None):
    doc_id, _ = await documents.write_agent_document(WS, doc_type, title, title + " text", "test", domain=domain)
    vectors = [vector(theme, spread), vector(theme, spread + 1)]
    await sections.store(doc_id, ([title + " part 1", title + " part 2"], vectors, sections.mean(vectors)))
    return doc_id


@pytest.fixture
def database():
    dsn = os.environ.get("GRAPH_TEST_RUNTIME_URL")
    if not dsn:
        pytest.skip("Disposable migrated Postgres with the horology_graph login is required")
    return dsn


def test_topics_are_built_named_kept_and_extended(database):
    from horology_runtime.database import Database
    names = iter([("Newsletter launch", "Launching the newsletter."), ("Pricing", "How we price."),
                  ("Should not be used", "")])
    fake = AsyncMock(side_effect=lambda *args, **kwargs: dict(zip(("name", "summary"), next(names))))

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM topics WHERE workspace = %s", (WS,))
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                newsletter = [await add(0, i, f"Newsletter {i}", domain="Newsletter") for i in range(3)]
                pricing = [await add(1, 10 + i, f"Pricing {i}", doc_type="decision" if i == 0 else "research")
                           for i in range(3)]
                with patch.object(naming.chat, "complete_json", fake):
                    first = await topics.rebuild(WS)
                    assert first["topics"] == 2 and first["new"] == 2 and first["named"] == 2
                    listed = await topics.list_topics(WS)
                    assert sorted(t["name"] for t in listed) == ["Newsletter launch", "Pricing"]
                    assert all(t["documents"] == 3 and t["sections"] == 6 for t in listed)
                    pricing_topic = next(t for t in listed if t["name"] == "Pricing")
                    assert pricing_topic["document_types"] == {"decision": 1, "research": 2}
                    assert [t["name"] for t in await topics.list_topics(WS, "newsletter")] == ["Newsletter launch"]

                    # A new newsletter document joins the existing topic without re-clustering.
                    later = await add(0, 50, "Newsletter growth", domain="Newsletter")
                    assert await topics.place_document(WS, later) == 2
                    topic_id = next(t["id"] for t in listed if t["name"] == "Newsletter launch")
                    detail = await topics.get_topic(WS, topic_id, passages=2)
                    assert later in {d["id"] for d in detail["documents"]}
                    assert len(detail["passages"]) == 2 and all(p["text"] for p in detail["passages"])

                    # Re-clustering keeps both topics and their names; nothing new to name.
                    second = await topics.rebuild(WS)
                    assert second["kept"] == 2 and second["new"] == 0 and second["named"] == 0 and fake.await_count == 2
                    again = {t["name"]: t["id"] for t in await topics.list_topics(WS)}
                    assert again["Newsletter launch"] == topic_id

                    assert await topics.list_topics("someone-else") == []
                    with pytest.raises(ValueError, match="No topic"):
                        await topics.get_topic("someone-else", topic_id)
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM topics WHERE workspace = %s", (WS,))
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                graph_core.configure(None)
    asyncio.run(run())


def test_a_failed_name_is_retried_on_the_next_rebuild(database):
    from horology_runtime.database import Database

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM topics WHERE workspace = %s", (WS,))
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                for i in range(3):
                    await add(0, i, f"Newsletter {i}")
                    await add(1, 10 + i, f"Pricing {i}")
                with patch.object(naming.chat, "complete_json", AsyncMock(side_effect=RuntimeError("down"))):
                    assert (await topics.rebuild(WS))["named"] == 0
                unnamed = await topics.list_topics(WS)
                assert unnamed and all(t["name"] == "(not named yet)" for t in unnamed)
                count = iter(range(100))
                namer = AsyncMock(side_effect=lambda *a, **k: {"name": f"Docs {next(count)}", "summary": "s"})
                with patch.object(naming.chat, "complete_json", namer):
                    assert (await topics.rebuild(WS))["named"] == len(unnamed)
                assert all(t["name"].startswith("Docs") for t in await topics.list_topics(WS))
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM topics WHERE workspace = %s", (WS,))
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                graph_core.configure(None)
    asyncio.run(run())
