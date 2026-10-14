"""Document links against a disposable migrated Postgres, as the horology_graph login."""
import asyncio

import pytest

import graph_core
from graph_core.documents import service as documents

WS = "documents-test"


def test_a_link_is_checked_and_added_in_one_statement(database):
    from horology_runtime.database import Database

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN (%s, 'elsewhere')", (WS,))
                first, _ = await documents.write_agent_document(WS, "research", "One", "One.", "test")
                second, _ = await documents.write_agent_document(WS, "research", "Two", "Two.", "test")
                other, _ = await documents.write_agent_document("elsewhere", "research", "Other", "Other.", "test")

                link = await documents.link(WS, first, second, "informed_by")
                assert link is not None
                assert await documents.link(WS, first, second, "informed_by") is None  # already there
                assert await documents.link(WS, first, first, "references") is not None  # the same id twice is fine
                for missing in (other, 999_999_999):  # another workspace's document, or none at all
                    with pytest.raises(ValueError, match="Both documents must exist"):
                        await documents.link(WS, first, missing, "informed_by")
                related = await documents.related(WS, first)
                assert sorted(r["relation"] for r in related if r["direction"] == "outgoing") == ["informed_by", "references"]
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace IN (%s, 'elsewhere')", (WS,))
                graph_core.configure(None)
    asyncio.run(run())


def test_sections_are_stored_in_one_round_trip_exactly_and_all_or_nothing(database):
    from horology_runtime.database import Database
    from graph_core.sections import service as sections

    tricky = ["It's a \"quote\"; DROP TABLE documents; --", "Back\\slash, 100% and %s and %(x)s", "Ünïcödé — ✓\nnew line"]
    vectors = [[0.1] * 768, [0.2] * 768, [0.3] * 768]

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                doc, _ = await documents.write_agent_document(WS, "research", "Tricky", "x", "test")
                await sections.store(doc, (tricky, vectors, sections.mean(vectors)))
                assert [text for _, text in await sections.of_document(doc)] == tricky

                # A failing statement (a vector of the wrong size) leaves the earlier sections in place.
                with pytest.raises(Exception):
                    await sections.store(doc, (["New"], [[0.1] * 5], [0.1] * 768))
                assert [text for _, text in await sections.of_document(doc)] == tricky
            finally:
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
                graph_core.configure(None)
    asyncio.run(run())
