"""Find named things and their relationships in a document's sections with the LLM."""
from ..providers import llm
from . import prompts
from .buckets import OTHER, normalize

BATCH_SECTIONS = 4  # sections per call; bigger batches made the model loop on long lists
BATCH_CHARS = 8_000  # ~2k tokens of document text per call
MAX_NAME = 120


def batches(sections):
    """Group [(index, text)] into calls of at most BATCH_SECTIONS sections / BATCH_CHARS characters."""
    group, size = [], 0
    for index, text in sections:
        if group and (len(group) == BATCH_SECTIONS or size + len(text) > BATCH_CHARS):
            yield group
            group, size = [], 0
        group.append((index, text))
        size += len(text)
    if group:
        yield group


async def extract(title, sections, buckets, relation_types):
    """Return (mentions, relations) for a document.

    mentions: [{"name", "key", "bucket", "suggested", "description", "sections"}], one per
    bucket + normalised name. relations: [(from key, relation type, to key, section)]."""
    bucket_names = {normalize(b): b for b in buckets}
    relation_names = {normalize(r): r for r in relation_types}
    found, relations = {}, []
    for group, reply in [item for batch in batches(sections) for item in await _ask(title, batch, buckets, relation_types)]:
        valid = {index for index, _ in group}
        names = {}
        for item in reply.get("mentions", []):
            name = " ".join(str(item.get("name", "")).split())[:MAX_NAME]
            key = normalize(name)
            if not key:
                continue
            bucket = bucket_names.get(normalize(item.get("bucket")))
            suggested = normalize(item.get("suggested_bucket")) or None
            if bucket is None:  # a bucket we don't have: park it in `other` with the suggestion
                bucket, suggested = OTHER, suggested or normalize(item.get("bucket")) or None
            if bucket != OTHER:
                suggested = None
            in_sections = {int(s) for s in item.get("sections", []) if int(s) in valid} or {group[0][0]}
            entry = found.setdefault((bucket, key), {"name": name, "key": key, "bucket": bucket, "suggested": suggested,
                                                     "description": "", "sections": set()})
            entry["sections"] |= in_sections
            if len(str(item.get("description", ""))) > len(entry["description"]):
                entry["description"] = str(item["description"]).strip()[:300]
            names[key] = (bucket, key)
        for item in reply.get("relations", []):
            source, target = names.get(normalize(item.get("from"))), names.get(normalize(item.get("to")))
            relation = relation_names.get(normalize(item.get("relation")))
            section = int(item.get("section", -1))
            if source and target and relation and source != target:
                relations.append((source, relation, target, section if section in valid else group[0][0]))
    return list(found.values()), relations


async def _ask(title, group, buckets, relation_types):
    """[(sections, reply)] for a batch; a cut-off reply is retried as two halves, down to one section.

    A single section whose reply is still cut off is skipped (logged by the caller's counts)."""
    shown = "\n\n".join(f"Section {index}:\n{text}" for index, text in group)
    user = (f"Buckets: {', '.join(buckets)}\nRelationship types: {', '.join(relation_types)}\n\n"
            f"Document title: {title}\n\n{shown}")
    reply = await llm.complete_json(prompts.EXTRACT_SYSTEM, user, "entities", prompts.EXTRACT_SCHEMA)
    if reply is not None:
        return [(group, reply)]
    if len(group) == 1:
        return []
    middle = len(group) // 2
    return await _ask(title, group[:middle], buckets, relation_types) + await _ask(title, group[middle:], buckets, relation_types)

