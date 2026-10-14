"""Find entities in documents, resolve them against known ones, and look them up."""
import asyncio
import logging

from horology_runtime.error_handling import category

from .. import database
from ..documents import fields
from ..documents import service as documents
from ..ai import embeddings
from ..sections import service as sections
from . import buckets, extraction, resolution
from .repository import EntityRepository

log = logging.getLogger("graph_core.entities")
RUN_LIMIT = 200  # documents per run; the rest wait for the next one
EXTRACT_CONCURRENCY = 4  # documents extracted at once; resolution stays one document at a time
STOP_AFTER_FAILURES = 5  # this many failed documents in a row means the provider is down: stop the run


def _repository():
    return EntityRepository(database.get())


async def types(workspace):
    """{'entity': {name: id}, 'relation': {name: id}}; seeds the defaults for a new workspace."""
    repository = _repository()
    rows = await repository.types(workspace)
    if not any(row["kind"] == "entity" for row in rows):
        await repository.add_types(workspace, "entity", buckets.DEFAULT_BUCKETS)
        await repository.add_types(workspace, "relation", buckets.DEFAULT_RELATIONS)
        rows = await repository.types(workspace)
    found = {"entity": {}, "relation": {}}
    for row in rows:
        found[row["kind"]][row["name"]] = row["id"]
    if buckets.OTHER not in found["entity"]:
        await repository.add_types(workspace, "entity", [(buckets.OTHER, dict(buckets.DEFAULT_BUCKETS)[buckets.OTHER])])
        return await types(workspace)
    return found


async def _extract(workspace, document_id, known):
    """LLM extraction for one document: no writes, so several can run at once."""
    document = await documents.get(workspace, document_id)
    if document is None:
        raise ValueError(f"No document with id {document_id}")
    section_rows = await sections.of_document(document_id)
    mentions, relations = await extraction.extract(document["title"], section_rows, list(known["entity"]),
                                                   list(known["relation"]))
    return section_rows, mentions, relations


async def _store(workspace, document_id, known, extracted):
    """Resolve and store one document's entities. Runs one document at a time, so two documents
    naming the same new thing can't both create it."""
    repository = _repository()
    section_rows, mentions, relations = extracted
    resolved, decisions = await resolution.resolve(repository, workspace, document_id, mentions, known["entity"],
                                                   dict(section_rows))
    mention_rows = [(resolved[(m["bucket"], m["key"])], section, m["name"]) for m in mentions for section in sorted(m["sections"])]
    relation_rows = [(resolved[source], known["relation"][relation], resolved[target], section)
                     for source, relation, target, section in relations
                     if source in resolved and target in resolved and resolved[source] != resolved[target]]
    await repository.replace_document(document_id, mention_rows, relation_rows)
    if decisions:
        await repository.log_decisions(decisions)
    return {"mentions": len(mentions), "relations": len(relation_rows),
            "new": sum(1 for d in decisions if d["decision"] == "new"),
            "matched": sum(1 for d in decisions if d["decision"] in ("exact", "same"))}


async def process_document(workspace, document_id):
    """Extract, resolve and store one document's entities and relationships. Returns counts."""
    known = await types(workspace)
    return await _store(workspace, document_id, known, await _extract(workspace, document_id, known))


async def process_pending(workspace, limit=RUN_LIMIT):
    """Process every document whose sections changed since its last run (agent and sheet documents).

    Extraction runs EXTRACT_CONCURRENCY documents at a time; resolution follows one by one.
    A failure marks that document 'failed' to retry next run; it stays searchable. After
    STOP_AFTER_FAILURES failures in a row the run stops; the rest stay pending for the next run."""
    repository = _repository()
    known = await types(workspace)
    pending = await repository.pending_documents(workspace, limit)
    summary = {"workspace": workspace, "documents": 0, "failed": 0, "new": 0, "matched": 0, "relations": 0,
               "stopped_early": False}
    failures_in_a_row = 0
    gate = asyncio.Semaphore(EXTRACT_CONCURRENCY)

    async def extract_one(document_id):
        async with gate:
            try:
                return await _extract(workspace, document_id, known)
            except Exception as error:
                return error

    step = EXTRACT_CONCURRENCY * 2  # extract a few ahead, then resolve them in order
    for start in range(0, len(pending), step):
        if summary["stopped_early"]:
            break
        chunk = pending[start:start + step]
        extracted = await asyncio.gather(*(extract_one(document_id) for document_id, _ in chunk))
        for (document_id, sections_hash), result in zip(chunk, extracted):
            try:
                if isinstance(result, Exception):
                    raise result
                counts = await _store(workspace, document_id, known, result)
            except Exception as error:
                log.warning("entities for document %s failed: %s", document_id, category(error))
                await repository.mark_run(document_id, sections_hash, "failed")
                summary["failed"] += 1
                failures_in_a_row += 1
                if failures_in_a_row >= STOP_AFTER_FAILURES:
                    log.warning("entities run stopped after %s failures in a row", failures_in_a_row)
                    summary["stopped_early"] = True
                    break
                continue
            failures_in_a_row = 0
            await repository.mark_run(document_id, sections_hash, "done")
            summary["documents"] += 1
            for key in ("new", "matched", "relations"):
                summary[key] += counts[key]
    log.info("entities processed %s", summary)
    return summary


# Lookups for agents

async def _type_id(workspace, bucket):
    if bucket is None:
        return None
    ids = {buckets.normalize(name): type_id for name, type_id in (await types(workspace))["entity"].items()}
    type_id = ids.get(buckets.normalize(bucket))
    if type_id is None:
        raise ValueError(f"Unknown bucket {bucket!r}; known buckets: {', '.join(sorted(ids))}")
    return type_id


async def list_entities(workspace, bucket=None, domain=None, limit=50):
    return await _repository().listing(workspace, await _type_id(workspace, bucket), fields.domain(domain), limit)


async def find_entity(workspace, name, bucket=None, limit=5):
    """Entities matching a name: exact name or alias first, otherwise the closest by meaning."""
    repository = _repository()
    type_id = await _type_id(workspace, bucket)
    ids = await repository.find_by_name(workspace, buckets.normalize(name), type_id)
    match = "exact"
    if not ids:
        ids = await repository.nearest(workspace, await embeddings.embed(name), limit, type_id)
        match = "closest"
    return {"match": match, "entities": await repository.cards(workspace, ids[:limit])}


async def entity_documents(workspace, entity_id, limit=10):
    """An entity's card plus the passages that name it, newest documents first."""
    repository = _repository()
    card = await repository.cards(workspace, [entity_id])
    if not card:
        raise ValueError(f"No entity with id {entity_id}")
    return {**card[0], "mentions": await repository.mentions(workspace, entity_id, limit)}


# Review tab edits

async def review_rows(workspace):
    return await _repository().review_rows(workspace)


async def rename(workspace, entity_id, name):
    return await _repository().rename(workspace, entity_id, name.strip(), buckets.normalize(name))


async def merge(workspace, source_id, target_id):
    return await _repository().merge(workspace, source_id, target_id)


async def apply_types(workspace, entity_rows, relation_rows, renames):
    """Save the Entity types tab: [(name, description)] per kind, renames [(type id, new name)].

    Entities waiting in `other` move to a bucket that now matches their suggestion."""
    repository = _repository()
    for type_id, name in renames:
        await repository.rename_type(workspace, type_id, name)
    if entity_rows:
        await repository.add_types(workspace, "entity", entity_rows)
    if relation_rows:
        await repository.add_types(workspace, "relation", relation_rows)
    known = (await types(workspace))["entity"]
    moved = 0
    for name, type_id in known.items():
        if name != buckets.OTHER:
            moved += await repository.move_bucket(workspace, known[buckets.OTHER], type_id, buckets.normalize(name))
    return moved


async def type_rows(workspace):
    await types(workspace)
    return await _repository().types(workspace)
