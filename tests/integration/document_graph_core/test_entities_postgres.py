"""Entities end to end against a disposable migrated Postgres, as the restricted horology_graph login.

The LLM and embeddings are faked: extraction replies are scripted per
document, and the judge says a mention is the same as a candidate when the
script says so.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

import graph_core
from graph_core.documents import service as documents
from graph_core.entities import service as entities
from graph_core.ai import chat, embeddings
from graph_core.sections import service as sections

from support.entities import WS, add_document, clean, fake_embed_many, fake_llm, vector


def test_entities_are_extracted_resolved_and_looked_up(database):
    from horology_runtime.database import Database
    calls = []

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                await clean(db)
                with patch.object(chat, "complete_json", fake_llm(calls)), \
                        patch.object(embeddings, "embed_many", AsyncMock(side_effect=fake_embed_many)), \
                        patch.object(embeddings, "embed", AsyncMock(side_effect=lambda t: fake_embed_many([t])[0])):
                    first = await add_document("Platforms", ["Beehiiv vs Substack.", "ConvertKit in Singapore. Webinars."])
                    one = await entities.process_pending(WS)
                    assert one == {"workspace": WS, "documents": 1, "failed": 0, "new": 5, "matched": 0, "relations": 1,
                                   "stopped_early": False, "remaining": 0}
                    # Mentions are also checked against entities created earlier from the same document.
                    assert calls == ["entity_matches"]

                    second = await add_document("Launch", ["Moving from beehiiv to Kit for SG founders."])
                    two = await entities.process_pending(WS)
                    # beehiiv: exact; Kit and SG: judged the same as ConvertKit and Singapore
                    assert two["documents"] == 1 and two["new"] == 0 and two["matched"] == 3 and len(calls) == 2
                    assert (await entities.process_pending(WS))["documents"] == 0  # unchanged: not read again

                    found = await entities.find_entity(WS, "kit")
                    assert found["match"] == "exact"
                    card = found["entities"][0]
                    assert card["name"] == "ConvertKit" and card["aliases"] == ["Kit"] and card["documents"] == 2
                    beehiiv = (await entities.find_entity(WS, "Beehiiv"))["entities"][0]
                    rels = {(r["relation"], r["entity"], r["evidence"]) for r in beehiiv["relationships"]}
                    assert ("competes with", "Substack", 1) in rels and ("competes with", "ConvertKit", 1) in rels

                    platforms = await entities.list_entities(WS, "Platform or tool")
                    assert [e["name"] for e in platforms][:1] == ["Beehiiv"] and len(platforms) == 3
                    other = await entities.list_entities(WS, "other")
                    assert [e["name"] for e in other] == ["Webinars"]
                    detail = await entities.entity_documents(WS, card["id"])
                    assert {m["document_id"] for m in detail["mentions"]} == {first, second}
                    assert any("Kit" in m["named_as"] for m in detail["mentions"])
                    with pytest.raises(ValueError, match="Unknown bucket"):
                        await entities.list_entities(WS, "planets")
                    assert (await entities.find_entity("someone-else", "Beehiiv"))["entities"] == []

                    # Promoting `other` suggestions: adding an "events" bucket moves Webinars into it.
                    assert await entities.apply_types(WS, [("events", "Online or offline events")], [], []) == 1
                    assert [e["name"] for e in await entities.list_entities(WS, "events")] == ["Webinars"]

                    # Review edits: rename keeps the old name as an alias; merge folds mentions and relations.
                    substack = (await entities.find_entity(WS, "Substack"))["entities"][0]
                    assert await entities.rename(WS, substack["id"], "Substack Inc")
                    assert (await entities.find_entity(WS, "substack"))["entities"][0]["name"] == "Substack Inc"
                    assert await entities.merge(WS, substack["id"], beehiiv["id"])
                    merged = (await entities.find_entity(WS, "Beehiiv"))["entities"][0]
                    assert "Substack" in merged["aliases"] and merged["documents"] == 2
                    assert not any(r["entity"] == "Beehiiv" for r in merged["relationships"])  # no self-links
                    assert not await entities.merge(WS, substack["id"], beehiiv["id"])  # already merged

                    # A changed document is read again; its old mentions are replaced, not added to.
                    edited = [vector(200)]
                    await sections.store(second, (["Moving from beehiiv to Kit. Edited."], edited, sections.mean(edited)))
                    assert (await entities.process_pending(WS))["documents"] == 1
            finally:
                await clean(db)
                graph_core.configure(None)
    asyncio.run(run())


def test_a_failed_extraction_is_retried(database):
    from horology_runtime.database import Database

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                await clean(db)
                await add_document("Platforms", ["Beehiiv vs Substack.", "ConvertKit in Singapore."])
                with patch.object(chat, "complete_json", AsyncMock(side_effect=RuntimeError("down"))):
                    assert (await entities.process_pending(WS))["failed"] == 1
                with patch.object(chat, "complete_json", fake_llm([])), \
                        patch.object(embeddings, "embed_many", AsyncMock(side_effect=fake_embed_many)):
                    assert (await entities.process_pending(WS))["documents"] == 1
            finally:
                await clean(db)
                graph_core.configure(None)
    asyncio.run(run())


def test_a_run_stops_after_failures_in_a_row(database, caplog):
    from horology_runtime.database import Database
    from horology_runtime.error_handling import SafeToolError

    async def run():
        async with Database(database, 2) as db:
            graph_core.configure(db)
            try:
                await clean(db)
                for number in range(entities.STOP_AFTER_FAILURES + 2):
                    await add_document(f"Doc {number}", [f"Text {number}."])
                # What observe raises when an OpenRouter call times out after its retries
                timeout = SafeToolError("timeout", "test-request")
                with patch.object(chat, "complete_json", AsyncMock(side_effect=timeout)):
                    summary = await entities.process_pending(WS)
                assert summary["failed"] == entities.STOP_AFTER_FAILURES and summary["stopped_early"] is True
                assert summary["remaining"] == 2  # the 5 failures wait for a later run, not a follow-up
                assert "failed: timeout" in caplog.text and "SafeToolError" not in caplog.text
                async with db.transaction() as conn, conn.cursor() as cur:
                    await cur.execute("SELECT count(*) FROM entity_runs r JOIN documents d ON d.id = r.document_id "
                                      "WHERE d.workspace = %s", (WS,))
                    assert (await cur.fetchone())[0] == entities.STOP_AFTER_FAILURES  # the other two wait
            finally:
                await clean(db)
                graph_core.configure(None)
    asyncio.run(run())
