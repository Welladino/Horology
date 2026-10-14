"""Document rows, document-to-document links and Document Index bookkeeping."""
from .. import database
from ..sections import service as sections
from .repository import DocumentRepository, LinkRepository

# Document Index Document Type values (Read Me tab), also used by agents.
VALID_DOC_TYPES = ("research", "direction", "plan", "decision", "report", "brand_guide", "guide",
                   "template", "pipeline", "content", "analysis", "recommendation")
AUTO_LINK_THRESHOLD = 0.85


def _documents():
    return DocumentRepository(database.get())


def _links():
    return LinkRepository(database.get())


def check_doc_type(doc_type):
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"doc_type must be one of {VALID_DOC_TYPES}, got {doc_type!r}")


async def all_exist(workspace, ids):
    ids = set(ids)
    return await _documents().count_existing(workspace, ids) == len(ids)


async def write_agent_document(workspace, doc_type, title, content, created_by_agent, supersedes_id=None):
    """Store an agent document; returns (id, created_at). Not searchable until embedded."""
    check_doc_type(doc_type)
    if supersedes_id is not None and not await all_exist(workspace, [supersedes_id]):
        raise ValueError(f"No document with id {supersedes_id}")
    return await _documents().insert_agent_document(workspace, doc_type, title, content, created_by_agent, supersedes_id)


async def get(workspace, document_id):
    return await _documents().get(workspace, document_id)


async def list_recent(workspace, doc_type, limit):
    if doc_type is not None:
        check_doc_type(doc_type)
    return await _documents().list(workspace, doc_type, limit)


async def related(workspace, document_id):
    return await _documents().related(workspace, document_id)


async def link(workspace, from_doc_id, to_doc_id, relation):
    """Return the new link id, or None when the edge already exists."""
    if not await all_exist(workspace, [from_doc_id, to_doc_id]):
        raise ValueError("Both documents must exist in your workspace")
    return await _links().add(from_doc_id, to_doc_id, relation)


async def unembedded(workspace):
    return await sections.documents_without_sections(workspace)


async def embed_if_needed(workspace, document_id):
    """Split and embed a document that has no sections yet. Raises if it doesn't exist."""
    row = await get(workspace, document_id)
    if row is None:
        raise ValueError(f"No document with id {document_id}")
    if not await sections.has_sections(document_id):
        # Outside any transaction; the HTTP calls can take seconds.
        await sections.store(document_id, await sections.embed_document(row["title"], row["content"]))


async def link_similar(workspace, document_id, threshold=AUTO_LINK_THRESHOLD):
    """Add related_to links above threshold; shared with the sheet sync job."""
    candidates = await sections.similar_documents(workspace, document_id)
    linked = []
    for other_id, similarity in candidates:
        if similarity >= threshold and await _links().add(document_id, other_id, "related_to") is not None:
            linked.append({"document_id": other_id, "similarity": round(float(similarity), 4)})
    return {"document_id": document_id, "newly_linked": linked, "candidates_checked": len(candidates)}


# Document Index sync

async def sheet_revisions(workspace):
    """Return {index_document_id: (graph id, imported Drive revision or None)} for sheet rows.

    The revision is None when the document has no sections yet, so a row
    imported before passage search, or whose import stopped before
    embedding, is imported again."""
    stored = await _documents().sheet_documents(workspace)
    embedded = await sections.with_sections([doc_id for doc_id, _ in stored.values()])
    return {key: (doc_id, revision if doc_id in embedded else None) for key, (doc_id, revision) in stored.items()}


async def store_sheet_document(workspace, index_document_id, drive_file_id, drive_url, doc_type, title, content, revision, embedded):
    """Insert or replace one sheet document with its already-computed embeddings; returns its graph id."""
    doc_id = await _documents().upsert_sheet_document(
        workspace, index_document_id, drive_file_id, drive_url, doc_type, title, content, revision)
    await sections.store(doc_id, embedded)
    return doc_id


async def set_supersedes(workspace, newer_id, older_id):
    await _documents().set_supersedes(workspace, newer_id, older_id)
    await _links().add(newer_id, older_id, "supersedes")


async def delete_sheet_documents(workspace, index_document_ids):
    return await _documents().delete_sheet_documents(workspace, index_document_ids)
