"""Decide which known entity each new mention is, or that it's new.

1. Exact: the normalised name or an alias already exists in the same bucket.
2. Shortlist: the 5 closest entities in the same bucket by embedding.
3. Judge: the LLM picks one of the shortlist, or none. No shortlist means new.
Every decision is logged for review and later tuning.
"""
from ..providers import embeddings, llm
from . import prompts

SHORTLIST = 5
JUDGE_BATCH = 20  # mentions per judge call
MERGE_CONFIDENCE = 0.6  # a less certain "same" creates a new entity instead (reviewable)
PASSAGE_CHARS = 400


async def resolve(repository, workspace, document_id, mentions, type_ids, passages):
    """Return {(bucket, key): entity id} for every mention, and the decision rows to log.

    type_ids: {bucket name: type id}. passages: {section: text}, for the judge."""
    resolved, decisions, waiting = {}, [], []
    for mention in mentions:
        entity_id = await repository.exact(workspace, type_ids[mention["bucket"]], mention["key"])
        if entity_id:
            resolved[(mention["bucket"], mention["key"])] = entity_id
            decisions.append(_row(workspace, document_id, mention, "exact", entity_id))
        else:
            waiting.append(mention)
    if not waiting:
        return resolved, decisions

    vectors = await embeddings.embed_many([f"{m['name']}: {m['description']}" for m in waiting])
    judged = []
    for mention, vector in zip(waiting, vectors):
        mention["vector"] = vector
        mention["candidates"] = await repository.shortlist(workspace, type_ids[mention["bucket"]], vector, SHORTLIST)
        if mention["candidates"]:
            judged.append(mention)
        else:
            await _create(repository, workspace, document_id, mention, type_ids, resolved, decisions, "nothing similar known")

    for start in range(0, len(judged), JUDGE_BATCH):
        batch = judged[start:start + JUDGE_BATCH]
        answers = await _judge(batch, passages)
        for position, mention in enumerate(batch):
            match, confidence, reason = answers.get(position, (0, None, "no answer"))
            ids = {c["id"] for c in mention["candidates"]}
            if match in ids and (confidence or 0) >= MERGE_CONFIDENCE:
                await repository.add_alias(match, mention["name"], mention["key"])
                resolved[(mention["bucket"], mention["key"])] = match
                decisions.append(_row(workspace, document_id, mention, "same", match, confidence, reason))
            else:
                await _create(repository, workspace, document_id, mention, type_ids, resolved, decisions, reason, confidence)
    return resolved, decisions


async def _judge(batch, passages):
    """{position: (match id or 0, confidence, reason)} from one LLM call."""
    blocks = []
    for position, mention in enumerate(batch):
        passage = passages.get(min(mention["sections"]), "")[:PASSAGE_CHARS]
        candidates = "\n".join(
            f"  - id {c['id']}: {c['name']}" + (f" (also: {', '.join(c['aliases'])})" if c["aliases"] else "")
            + (f" — {c['description']}" if c["description"] else "")
            for c in mention["candidates"])
        blocks.append(f"Mention {position}: {mention['name']} [{mention['bucket']}] — {mention['description']}\n"
                      f"  Passage: {passage}\n  Candidates:\n{candidates}")
    reply = await llm.complete_json(prompts.JUDGE_SYSTEM, "\n\n".join(blocks), "entity_matches", prompts.JUDGE_SCHEMA)
    answers = {}
    for item in (reply or {}).get("decisions", []):  # a cut-off reply leaves every mention new
        position = int(item.get("mention", -1))
        if 0 <= position < len(batch):
            confidence = float(item.get("confidence", 0))
            answers[position] = (int(item.get("match", 0)), max(0.0, min(1.0, confidence)), str(item.get("reason", ""))[:300])
    return answers


async def _create(repository, workspace, document_id, mention, type_ids, resolved, decisions, reason, confidence=None):
    entity_id = await repository.create(workspace, type_ids[mention["bucket"]], mention["name"], mention["description"],
                                        mention["suggested"], mention["vector"], mention["key"])
    resolved[(mention["bucket"], mention["key"])] = entity_id
    decisions.append(_row(workspace, document_id, mention, "new", entity_id, confidence, reason))


def _row(workspace, document_id, mention, decision, entity_id, confidence=None, reason=None):
    return {"workspace": workspace, "document_id": document_id, "mention": mention["name"], "bucket": mention["bucket"],
            "description": mention["description"], "decision": decision, "entity_id": entity_id,
            "candidates": [{"id": c["id"], "name": c["name"], "similarity": round(float(c["similarity"]), 4)}
                           for c in mention.get("candidates", [])],
            "confidence": confidence, "reason": reason, "model": llm.LLM_MODEL if decision != "exact" else None}
