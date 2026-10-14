"""Scripted LLM and embedding fakes for entity tests, and document set-up and clean-up."""
import math

from graph_core.documents import service as documents
from graph_core.sections import service as sections

WS = "entities-test"


def vector(seed):
    v = [0.0] * 768
    v[seed % 768] = 1.0
    v[(seed * 7 + 3) % 768] = 0.3
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


SEEDS = {"Beehiiv": 1, "beehiiv": 1, "Substack": 2, "ConvertKit": 3, "Kit": 3, "Singapore": 4, "SG": 4}


def fake_embed_many(texts):
    return [vector(SEEDS.get(text.split(":")[0], 99)) for text in texts]


def mention(name, bucket, sections, description="", suggested=""):
    return {"name": name, "bucket": bucket, "suggested_bucket": suggested, "description": description or name,
            "sections": sections}


EXTRACTIONS = {
    "Platforms": {"mentions": [mention("Beehiiv", "platform or tool", [0], "Newsletter platform"),
                               mention("Substack", "platform or tool", [0, 1], "Newsletter platform"),
                               mention("ConvertKit", "platform or tool", [1], "Email platform"),
                               mention("Singapore", "market or country", [1], "Country"),
                               mention("Webinars", "events", [1], "Online events")],  # unknown bucket -> other
                  "relations": [{"from": "Beehiiv", "relation": "competes with", "to": "Substack", "section": 0},
                                {"from": "Beehiiv", "relation": "loves", "to": "Substack", "section": 0}]},  # unknown type
    "Launch": {"mentions": [mention("beehiiv", "platform or tool", [0], "Newsletter platform"),
                            mention("Kit", "platform or tool", [0], "Email platform, formerly ConvertKit"),
                            mention("SG", "market or country", [0], "Singapore")],
               "relations": [{"from": "beehiiv", "relation": "competes with", "to": "Kit", "section": 0}]},
}
SAME = {"Kit": "ConvertKit", "SG": "Singapore"}  # what the judge decides


def fake_llm(title_by_call):
    async def complete(system, user, schema_name, schema, max_tokens=4096, model=None):
        if schema_name == "entities":
            title = next(t for t in EXTRACTIONS if f"Document title: {t}" in user)
            return EXTRACTIONS[title]
        decisions = []
        for block in user.split("\n\n"):
            if not block.startswith("Mention "):
                continue
            position = int(block.split()[1].rstrip(":"))
            name = block.split(":", 1)[1].split("[")[0].strip()
            match = 0
            for line in block.splitlines():
                if "id " in line and SAME.get(name) and SAME[name] in line:
                    match = int(line.split("id ")[1].split(":")[0])
            decisions.append({"mention": position, "match": match, "confidence": 0.9, "reason": "test"})
        title_by_call.append(schema_name)
        return {"decisions": decisions}
    return complete


async def add_document(title, sections_text):
    doc_id, _ = await documents.write_agent_document(WS, "research", title, "\n\n".join(sections_text), "test")
    vectors = [vector(100 + i) for i, _ in enumerate(sections_text)]
    await sections.store(doc_id, (sections_text, vectors, sections.mean(vectors)))
    return doc_id


async def clean(db):
    async with db.transaction() as conn, conn.cursor() as cur:
        await cur.execute("DELETE FROM entity_decisions WHERE workspace = %s", (WS,))
        await cur.execute("DELETE FROM entity_relations r USING entities e WHERE e.id = r.from_entity AND e.workspace = %s", (WS,))
        await cur.execute("UPDATE entities SET merged_into = NULL WHERE workspace = %s", (WS,))
        await cur.execute("DELETE FROM entities WHERE workspace = %s", (WS,))
        await cur.execute("DELETE FROM entity_types WHERE workspace = %s", (WS,))
        await cur.execute("DELETE FROM documents WHERE workspace = %s", (WS,))
