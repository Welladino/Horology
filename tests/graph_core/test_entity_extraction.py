"""Entity extraction parsing and cut-off handling; the LLM is faked."""
import asyncio
from unittest.mock import patch

from graph_core.entities import extraction
from graph_core.entities.buckets import normalize
from graph_core.ai import chat

BUCKETS = ["company", "platform or tool", "other"]
RELATIONS = ["competes with", "uses"]


def run(coro):
    return asyncio.run(coro)


def test_batches_respect_section_and_size_limits():
    sections = [(i, "x" * 3000) for i in range(7)]
    groups = list(extraction.batches(sections))
    assert all(len(g) <= extraction.BATCH_SECTIONS and sum(len(t) for _, t in g) <= extraction.BATCH_CHARS or len(g) == 1
               for g in groups)
    assert [i for g in groups for i, _ in g] == list(range(7))


def test_a_cut_off_reply_is_retried_in_halves_and_a_hopeless_section_skipped():
    calls = []

    async def fake(system, user, schema_name, schema, max_tokens=4096):
        shown = [int(line.split()[1].rstrip(":")) for line in user.splitlines() if line.startswith("Section ")]
        calls.append(shown)
        if len(shown) > 1 or shown == [3]:  # only single sections answer, and section 3 always loops
            return None
        return {"mentions": [{"name": f"Thing {shown[0]}", "bucket": "company", "suggested_bucket": "",
                              "description": "d", "sections": shown}], "relations": []}
    with patch.object(chat, "complete_json", fake):
        mentions, _ = run(extraction.extract("T", [(i, "text") for i in range(4)], BUCKETS, RELATIONS))
    assert sorted(m["name"] for m in mentions) == ["Thing 0", "Thing 1", "Thing 2"]
    assert calls[0] == [0, 1, 2, 3] and [3] in calls


def test_buckets_relations_and_duplicates_are_cleaned():
    async def fake(system, user, schema_name, schema, max_tokens=4096):
        return {"mentions": [
            {"name": " Shopify ", "bucket": "Platform or Tool", "suggested_bucket": "x", "description": "store builder", "sections": [0, 9]},
            {"name": "shopify.", "bucket": "platform or tool", "suggested_bucket": "", "description": "longer store builder text", "sections": [1]},
            {"name": "Webinars", "bucket": "events", "suggested_bucket": "", "description": "events", "sections": [1]},
            {"name": "  ", "bucket": "company", "suggested_bucket": "", "description": "", "sections": [0]}],
            "relations": [
                {"from": "Shopify", "relation": "Competes With", "to": "Webinars", "section": 1},
                {"from": "Shopify", "relation": "loves", "to": "Webinars", "section": 1},
                {"from": "Shopify", "relation": "uses", "to": "Nobody", "section": 1},
                {"from": "shopify", "relation": "uses", "to": "Shopify", "section": 1}]}
    with patch.object(chat, "complete_json", fake):
        mentions, relations = run(extraction.extract("T", [(0, "a"), (1, "b")], BUCKETS, RELATIONS))
    by_key = {m["key"]: m for m in mentions}
    assert set(by_key) == {"shopify", "webinars"}
    shopify = by_key["shopify"]
    assert shopify["bucket"] == "platform or tool" and shopify["suggested"] is None
    assert shopify["sections"] == {0, 1} and shopify["description"] == "longer store builder text"
    assert by_key["webinars"]["bucket"] == "other" and by_key["webinars"]["suggested"] == "events"
    assert relations == [(("platform or tool", "shopify"), "competes with", ("other", "webinars"), 1)]
    assert normalize("  LinkedIn. ") == "linkedin"
