"""Split documents into sections, embed them, and find passages and similar documents."""
import math

from .. import database
from ..documents import fields
from ..ai import embeddings
from . import chunking
from .chunking import MAX_SECTIONS, TooLong  # noqa: F401  (for callers that report the limit)
from .repository import SectionRepository


def _repository():
    return SectionRepository(database.get())


def check_length(content):
    """Raise TooLong if the document has more than MAX_SECTIONS sections. Local; costs nothing."""
    count = len(chunking.split(content))
    if count > MAX_SECTIONS:
        raise TooLong(count)


async def embed_document(title, content):
    """Split a document into sections and embed each one, titled for context.

    Returns (sections, section vectors, document vector); the document vector
    is the normalised mean of its sections, used for auto-linking. Makes the
    embedding calls only; nothing is stored. Raises TooLong before any call."""
    sections = chunking.split(content) or [title]
    if len(sections) > MAX_SECTIONS:
        raise TooLong(len(sections))
    vectors = await embeddings.embed_many([f"{title}\n\n{section}" for section in sections])
    return sections, vectors, mean(vectors)


def mean(vectors):
    total = [sum(values) for values in zip(*vectors)]
    norm = math.sqrt(sum(x * x for x in total)) or 1.0
    return [x / norm for x in total]


async def store(document_id, embedded):
    """Replace a document's sections and document vector in one transaction."""
    await _repository().save(document_id, *embedded)


async def to_embed(workspace, document_id):
    """(title, content, has sections) for a document in the workspace; None if there's none."""
    return await _repository().to_embed(workspace, document_id)


async def has_sections(document_id):
    return await _repository().has_sections(document_id)


async def with_sections(document_ids):
    return await _repository().with_sections(document_ids)


async def documents_without_sections(workspace):
    return await _repository().documents_without_sections(workspace)


async def similar_documents(workspace, document_id):
    """(other document id, cosine similarity) for every other embedded document, best first."""
    return await _repository().similar_to(workspace, document_id)


async def search_passages(workspace, query, limit, passages, domain=None):
    """Closest documents to the query, best section first, each with its top passages."""
    vector = await embeddings.embed(query)
    # Sections are ranked across documents; fetch enough to fill `limit` documents.
    sections = await _repository().nearest_sections(workspace, vector, min(limit * 8, 200), fields.domain(domain))
    results = {}
    for row in sections:
        similarity = round(float(row.pop("similarity")), 4)
        passage = {"section": row.pop("chunk_index"), "similarity": similarity, "text": row.pop("passage")}
        if row["id"] not in results:
            if len(results) == limit:
                continue
            results[row["id"]] = {**row, "created_at": row["created_at"].isoformat(), "similarity": similarity, "passages": []}
        if len(results[row["id"]]["passages"]) < passages:
            results[row["id"]]["passages"].append(passage)
    return list(results.values())


LINK_BATCH_DOCUMENTS = 15  # up to 450 sections per neighbour query, well inside the 10-second statement limit


async def neighbour_links(workspace, k, floor, document_id=None):
    """Similarity links between sections of different documents (the topic graph's edges)."""
    repository = _repository()
    ids = [document_id] if document_id is not None else await repository.document_ids(workspace)
    links = []
    for start in range(0, len(ids), LINK_BATCH_DOCUMENTS):
        links += await repository.neighbour_links(workspace, k, floor, ids[start:start + LINK_BATCH_DOCUMENTS])
    return links


async def texts(keys):
    return await _repository().texts(keys)


async def of_document(document_id):
    return await _repository().of_document(document_id)

