"""Document graph MCP tools: validate input, scope to the caller's workspace, call graph_core.

The logic lives in document-graph-core (shared with the sync job); this
module only turns tool calls into service calls.
"""
from graph_core.documents import service as documents
from graph_core.documents.service import VALID_DOC_TYPES  # noqa: F401  (re-exported for callers and tests)
from graph_core.sections import service as sections

from .integrations.cloud_run import client as cloud_run
from .shared.workspace import current_workspace


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
) -> dict:
    """Write a new document to the document graph in your workspace.

    doc_type must be one of: research, direction, plan, decision, report,
    brand_guide, guide, template, pipeline, content, analysis, recommendation.
    Use supersedes_id to link this document as replacing an earlier one
    (creates a version chain rather than an orphaned duplicate).
    Returns the new document's id.
    """
    new_id, created_at = await documents.write_agent_document(
        current_workspace(), doc_type, title, content, created_by_agent, supersedes_id)
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


async def list_documents(doc_type: str | None = None, limit: int = 20) -> list[dict]:
    """List documents, most recent first, optionally filtered by doc_type.

    Returns title/metadata only, not full content — use get_document for
    the full text of a specific one.
    """
    return _iso(await documents.list_recent(current_workspace(), doc_type, max(1, min(limit, 100))))


async def search_documents(query: str, limit: int = 5, passages: int = 2) -> list[dict]:
    """Find documents by meaning: "what have we done on pricing?".

    Searches every section of every document in your workspace and returns
    the closest documents (up to limit), best first. Each result has a
    similarity score (0-1, from its best section) and up to `passages`
    (1-3) matching sections of about 2,000 characters each, with their
    section number. Read the passages first; use get_document only when you
    need the whole text.
    """
    if not query.strip():
        raise ValueError("query must not be empty")
    return await sections.search_passages(current_workspace(), query, max(1, min(limit, 20)), max(1, min(passages, 3)))


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
    return await documents.link_similar(workspace, document_id, threshold)


async def sync_graph() -> dict:
    """Start the Document Index -> graph sync for your workspace.

    The job imports rows whose Graph Inclusion is TRUE (re-embedding only
    changed documents), removes rows set to FALSE, and writes Graph Sync
    Status back to the sheet. It runs in the background; this returns as
    soon as it has started. Check the sheet's Graph Sync Status column for
    results.
    """
    workspace = current_workspace()
    operation = await cloud_run.start_sync(workspace)
    return {"started": True, "workspace": workspace, "operation": operation}
