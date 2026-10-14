"""Split documents into sections, embed them, and find passages and similar documents."""
import math

from .. import database
from ..providers import embeddings
from . import chunking
from .repository import SectionRepository


def _repository():
    return SectionRepository(database.get())


async def embed_document(title, content):
    """Split a document into sections and embed each one, titled for context.

    Returns (sections, section vectors, document vector); the document vector
    is the normalised mean of its sections, used for auto-linking. Makes the
    embedding calls only; nothing is stored."""
    sections = chunking.split(content) or [title]
    vectors = await embeddings.embed_many([f"{title}\n\n{section}" for section in sections])
    return sections, vectors, mean(vectors)


def mean(vectors):
    total = [sum(values) for values in zip(*vectors)]
    norm = math.sqrt(sum(x * x for x in total)) or 1.0
    return [x / norm for x in total]


async def store(document_id, embedded):
    """Replace a document's sections and document vector in one transaction."""
    await _repository().save(document_id, *embedded)


async def has_sections(document_id):
    return await _repository().has_sections(document_id)


async def with_sections(document_ids):
    return await _repository().with_sections(document_ids)


async def documents_without_sections(workspace):
    return await _repository().documents_without_sections(workspace)


async def similar_documents(workspace, document_id):
    """(other document id, cosine similarity) for every other embedded document, best first."""
    return await _repository().similar_to(workspace, document_id)


async def search_passages(workspace, query, limit, passages):
    """Closest documents to the query, best section first, each with its top passages."""
    vector = await embeddings.embed(query)
    # Sections are ranked across documents; fetch enough to fill `limit` documents.
    sections = await _repository().nearest_sections(workspace, vector, min(limit * 8, 200))
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
