"""Document graph MCP tools: validate input, scope to the caller's workspace, call graph_core.

The logic lives in document-graph-core (shared with the sync job); this
module only turns tool calls into service calls.
"""
from graph_core.documents import service as documents
from graph_core.entities import service as entities
from graph_core.documents.service import VALID_DOC_TYPES  # noqa: F401  (re-exported for callers and tests)
from graph_core.runs import service as runs
from graph_core.sections import service as sections
from graph_core.topics import service as topics
import logging
from horology_runtime.error_handling import category

from .shared.workspace import current_workspace

log = logging.getLogger("document_graph")


def _iso(rows):
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
    return rows


async def write_document(
    doc_type: str,
    title: str,
    content: str,
    created_by_agent: str,
    supersedes_id: int | None = None,
    domain: str | None = None,
    pipeline_id: int | None = None,
) -> dict:
    """Write a new document to the document graph in your workspace.

    doc_type must be one of: research, direction, plan, decision, report,
    brand_guide, guide, template, pipeline, content, analysis, recommendation.
    Use supersedes_id to link this document as replacing an earlier one
    (creates a version chain rather than an orphaned duplicate).
    Pass domain (e.g. Welladino, Newsletter) and the permanent Pipeline ID
    of the item you are working on when there is one.
    Returns the new document's id. A document over 30 sections (about 20
    pages) is not saved: the reply says so; split it into parts and write each.
    """
    try:
        new_id, created_at = await documents.write_agent_document(
            current_workspace(), doc_type, title, content, created_by_agent, supersedes_id, domain, pipeline_id)
    except sections.TooLong as error:
        # Returned, not raised: tool errors reach the agent as a category only.
        return {"saved": False, "reason": "too_long", "sections": error.sections, "limit": sections.MAX_SECTIONS,
                "next_step": "Split it into parts of about 20 pages, write each part, and link them with link_documents."}
    return {"id": new_id, "created_at": created_at.isoformat()}


async def link_documents(from_doc_id: int, to_doc_id: int, relation: str) -> dict:
    """Create a relationship edge between two existing documents in your workspace.

    relation is free text describing the relationship (e.g. informed_by,
    supersedes, contradicts, references). Duplicate edges (same
    from/to/relation triple) are ignored rather than erroring.
    """
    link_id = await documents.link(current_workspace(), from_doc_id, to_doc_id, relation)
    if link_id is None:
        return {"created": False, "reason": "link already exists"}
    return {"created": True, "id": link_id}


async def get_document(id: int) -> dict:
    """Fetch a single document by id, including its full content."""
    row = await documents.get(current_workspace(), id)
    if row is None:
        raise ValueError(f"No document with id {id}")
    return _iso([row])[0]


async def list_documents(doc_type: str | None = None, limit: int = 20, domain: str | None = None) -> list[dict]:
    """List documents, most recent first, optionally filtered by doc_type and domain.

    Returns title/metadata only (including domain, business_entity and
    pipeline_id), not full content — use get_document for the full text.
    """
    return _iso(await documents.list_recent(current_workspace(), doc_type, max(1, min(limit, 100)), domain))


async def search_documents(query: str, limit: int = 5, passages: int = 2, domain: str | None = None) -> list[dict]:
    """Find documents by meaning: "what have we done on pricing?".

    Searches every section of every document in your workspace and returns
    the closest documents (up to limit), best first. Each result has a
    similarity score (0-1, from its best section) and up to `passages`
    (1-3) matching sections of about 2,000 characters each, with their
    section number. Read the passages first; use get_document only when you
    need the whole text. Pass domain (e.g. Newsletter) to search one domain;
    results include each document's domain, business_entity and pipeline_id.
    """
    if not query.strip():
        raise ValueError("query must not be empty")
    return await sections.search_passages(current_workspace(), query, max(1, min(limit, 20)), max(1, min(passages, 3)), domain)


async def get_related_documents(document_id: int) -> list[dict]:
    """Return every document linked to or from the given document, via
    document_links - both auto-created ('related_to', from
    auto_link_similar_documents) and manually-created edges (e.g.
    supersedes, contradicts, informed_by).

    Each result includes the related document's id/title/doc_type, the
    relation, and direction ('outgoing' if this document points to it,
    'incoming' if it points to this document). Does not include content -
    use get_document for that.
    """
    return await documents.related(current_workspace(), document_id)


async def list_unembedded_documents() -> list[dict]:
    """Return every document in your workspace that has no searchable
    sections yet - written before passage search existed, or where a prior
    auto_link_similar_documents call was skipped or failed before completing.

    Each returned id can be passed directly into auto_link_similar_documents
    to backfill it. Normally returns few or zero rows - a non-empty result
    means something to catch up on, not a broken system.
    """
    return _iso(await documents.unembedded(current_workspace()))


async def auto_link_similar_documents(document_id: int, threshold: float = 0.85) -> dict:
    """Embed a document and compare it against the other documents in your
    workspace, creating a 'related_to' link for any pair scoring above the
    cosine-similarity threshold (0-1, default 0.85).

    Call this once after writing a new document, passing its id. It first
    splits the document into searchable sections and embeds them if that
    hasn't happened yet; until then the document can't be found by search.
    Idempotent - re-running for the same document just re-checks and
    re-creates any missing links; existing links are never duplicated.
    Returns which document ids (if any) were newly linked.
    """
    workspace = current_workspace()
    await documents.embed_if_needed(workspace, document_id)
    result = await documents.link_similar(workspace, document_id, threshold)
    try:
        result["sections_placed_in_topics"] = await topics.place_document(workspace, document_id)
    except Exception as error:
        # Topics never block search: the document is already embedded and linked.
        log.warning("topic placement failed for %s: %s", document_id, category(error))
        result["sections_placed_in_topics"] = 0
    return result


async def sync_graph() -> dict:
    """Start the Document Index -> graph sync for your workspace.

    The job imports rows whose Graph Inclusion is TRUE (re-embedding only
    changed documents), removes rows set to FALSE, and writes Graph Sync
    Status back to the sheet. It runs in the background; this returns as
    soon as it has started. Check the sheet's Graph Sync Status column for
    results. A run handles up to 30 changed documents and starts the next
    run itself for the rest. Not started (started: false) when a run is
    already in progress, or the same request was made in the last 5
    minutes (retry_after_seconds says when to ask again).
    """
    workspace = current_workspace()
    return {"workspace": workspace, **await runs.request(workspace, "sync")}


async def list_topics(domain: str | None = None) -> list[dict]:
    """List the themes in your workspace's documents, largest first.

    Topics are found automatically by grouping similar passages from
    different documents. Each has a name, a one-sentence summary, how many
    documents and sections it covers, and its mix of document types (for
    example research but no decision yet). Pass domain (e.g. Newsletter) to
    count only that domain's documents. Use get_topic for documents and
    passages.
    """
    return await topics.list_topics(current_workspace(), domain)


async def get_topic(topic_id: int, passages: int = 3) -> dict:
    """Show one topic: its documents (with the share of each that falls in
    the topic, document type and Pipeline ID) and its strongest passages
    (up to 5)."""
    return await topics.get_topic(current_workspace(), topic_id, max(1, min(passages, 5)))


async def rebuild_topics() -> dict:
    """Start re-grouping your workspace's passages into topics.

    New documents join existing topics automatically; run this after many
    new documents, or when topics look stale. Topics that mostly continue
    keep their names; new ones are named automatically. It runs in the
    background and returns as soon as it has started. Not started when a run
    is in progress or this was asked for in the last 5 minutes.
    """
    workspace = current_workspace()
    return {"workspace": workspace, **await runs.request(workspace, "topics")}


async def list_entities(bucket: str | None = None, domain: str | None = None, limit: int = 50) -> list[dict]:
    """List the named things found in your workspace's documents, most documents first.

    Entities are companies, products, platforms and tools, our own system
    components, markets, audience segments, channels, people, features and
    metrics (and "other"). Filter by bucket (e.g. "platform or tool") for a
    complete list such as every platform we have looked at, and by domain.
    """
    return await entities.list_entities(current_workspace(), bucket, domain, max(1, min(limit, 200)))


async def find_entity(name: str, bucket: str | None = None) -> dict:
    """Look up a named thing by any of its names ("Kit" finds ConvertKit).

    Returns match "exact" (a known name or alias) or "closest" (nearest by
    meaning) with up to 5 entities: bucket, aliases, how many documents
    mention it, and its relationships (competes with, uses, targets, ...)
    with how many passages support each. Use entity_documents for passages.
    """
    if not name.strip():
        raise ValueError("name must not be empty")
    return await entities.find_entity(current_workspace(), name, bucket)


async def entity_documents(entity_id: int, limit: int = 10) -> dict:
    """Everything about one entity: its details, relationships and the
    passages that name it (newest documents first, up to 50), with each
    document's type, domain and Pipeline ID."""
    return await entities.entity_documents(current_workspace(), entity_id, max(1, min(limit, 50)))

