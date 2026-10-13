"""Document graph operations exposed as MCP tools, scoped to the caller's workspace.

SQL lives in database/repositories; this module holds validation, workspace
scoping and the embed-then-link steps.
"""
from .database.repositories.documents import DocumentRepository
from .database.repositories.embeddings import EmbeddingRepository
from .database.repositories.links import LinkRepository
from .integrations.cloud_run import client as cloud_run
from .integrations.openrouter import client as openrouter
from .shared.workspace import current_workspace

# Document Index Document Type values (Read Me tab), also used by agents.
VALID_DOC_TYPES = ("research", "direction", "plan", "decision", "report", "brand_guide", "guide",
                   "template", "pipeline", "content", "analysis", "recommendation")

documents = embeddings = links = None


def configure(database):
    """Bind the repositories to the shared pool; the server lifespan calls this."""
    global documents, embeddings, links
    documents, embeddings, links = (None, None, None) if database is None else (
        DocumentRepository(database), EmbeddingRepository(database), LinkRepository(database))


def _check_doc_type(doc_type):
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"doc_type must be one of {VALID_DOC_TYPES}, got {doc_type!r}")


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
    _check_doc_type(doc_type)
    workspace = current_workspace()
    if supersedes_id is not None and await documents.count_existing(workspace, [supersedes_id]) != 1:
        raise ValueError(f"No document with id {supersedes_id}")
    new_id, created_at = await documents.insert_agent_document(
        workspace, doc_type, title, content, created_by_agent, supersedes_id)
    return {"id": new_id, "created_at": created_at.isoformat()}


async def link_documents(from_doc_id: int, to_doc_id: int, relation: str) -> dict:
    """Create a relationship edge between two existing documents in your workspace.

    relation is free text describing the relationship (e.g. informed_by,
    supersedes, contradicts, references). Duplicate edges (same
    from/to/relation triple) are ignored rather than erroring.
    """
    ids = {from_doc_id, to_doc_id}
    if await documents.count_existing(current_workspace(), ids) != len(ids):
        raise ValueError("Both documents must exist in your workspace")
    link_id = await links.add(from_doc_id, to_doc_id, relation)
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
    if doc_type is not None:
        _check_doc_type(doc_type)
    return _iso(await documents.list(current_workspace(), doc_type, max(1, min(limit, 100))))


async def search_documents(query: str, limit: int = 5) -> list[dict]:
    """Find documents by meaning: "what have we done on pricing?".

    Embeds the query and returns the closest documents in your workspace,
    with a similarity score (0-1). Returns titles/metadata only — use
    get_document for the full text.
    """
    if not query.strip():
        raise ValueError("query must not be empty")
    vector = await openrouter._embed(query)
    rows = _iso(await embeddings.nearest(current_workspace(), vector, max(1, min(limit, 20))))
    for row in rows:
        row["similarity"] = round(float(row["similarity"]), 4)
    return rows


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
    """Return every document in your workspace that has no stored embedding
    yet - written before auto-linking existed, or where a prior
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

    Call this once after writing a new document, passing its id. Backfills
    the document's own embedding first if it doesn't have one yet.
    Idempotent - re-running for the same document just re-checks and
    re-creates any missing links; existing links are never duplicated.
    Returns which document ids (if any) were newly linked.
    """
    workspace = current_workspace()
    content = await documents.content(workspace, document_id)
    if content is None:
        raise ValueError(f"No document with id {document_id}")
    if not await embeddings.exists(document_id):
        # Outside any transaction; the HTTP call can take seconds.
        await embeddings.save(document_id, await openrouter._embed(content))
    return await link_similar(workspace, document_id, threshold)


async def link_similar(workspace, document_id, threshold):
    """Add related_to links above threshold; shared with the sheet sync job."""
    candidates = await embeddings.similar_to(workspace, document_id)
    linked = []
    for other_id, similarity in candidates:
        if similarity >= threshold and await links.add(document_id, other_id, "related_to") is not None:
            linked.append({"document_id": other_id, "similarity": round(float(similarity), 4)})
    return {"document_id": document_id, "newly_linked": linked, "candidates_checked": len(candidates)}


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
