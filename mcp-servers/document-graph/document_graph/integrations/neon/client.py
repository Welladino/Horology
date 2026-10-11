"""Fixed parameterized Neon document queries and graph orchestration."""
import os
from horology_runtime.settings import TIMEOUTS
import psycopg2
import psycopg2.extras
from ..openrouter import client as openrouter

VALID_DOC_TYPES = ("recommendation", "content", "analysis", "report")
DATABASE_URL_POOLED = os.environ.get("DATABASE_URL_POOLED")
if not DATABASE_URL_POOLED:
    raise RuntimeError("DATABASE_URL_POOLED is not set in this server's environment.")

def _connect():
    return psycopg2.connect(DATABASE_URL_POOLED, connect_timeout=TIMEOUTS.database_connect, options=TIMEOUTS.neon_options)

def write_document(
    doc_type: str,
    title: str,
    content: str,
    created_by_agent: str,
    supersedes_id: int | None = None,
) -> dict:
    """Write a new document to the document graph.

    doc_type must be one of: recommendation, content, analysis, report.
    Use supersedes_id to link this document as replacing an earlier one
    (creates a version chain rather than an orphaned duplicate).
    Returns the new document's id.
    """
    if doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"doc_type must be one of {VALID_DOC_TYPES}, got {doc_type!r}")

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (doc_type, title, content, created_by_agent, supersedes_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (doc_type, title, content, created_by_agent, supersedes_id),
        )
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "created_at": row[1].isoformat()}

def link_documents(from_doc_id: int, to_doc_id: int, relation: str) -> dict:
    """Create a relationship edge between two existing documents.

    relation is free text describing the relationship (e.g. informed_by,
    supersedes, contradicts, references). Duplicate edges (same
    from/to/relation triple) are ignored rather than erroring.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO document_links (from_doc_id, to_doc_id, relation)
            VALUES (%s, %s, %s)
            ON CONFLICT (from_doc_id, to_doc_id, relation) DO NOTHING
            RETURNING id
            """,
            (from_doc_id, to_doc_id, relation),
        )
        row = cur.fetchone()
        conn.commit()
        if row is None:
            return {"created": False, "reason": "link already exists"}
        return {"created": True, "id": row[0]}

def get_document(id: int) -> dict:
    """Fetch a single document by id, including its full content."""
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, doc_type, title, content, created_by_agent, supersedes_id, created_at
            FROM documents WHERE id = %s
            """,
            (id,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No document with id {id}")
        result = dict(row)
        result["created_at"] = result["created_at"].isoformat()
        return result

def list_documents(doc_type: str | None = None, limit: int = 20) -> list[dict]:
    """List documents, most recent first, optionally filtered by doc_type.

    Returns title/metadata only, not full content — use get_document for
    the full text of a specific one.
    """
    if doc_type is not None and doc_type not in VALID_DOC_TYPES:
        raise ValueError(f"doc_type must be one of {VALID_DOC_TYPES}, got {doc_type!r}")
    limit = max(1, min(limit, 100))

    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if doc_type is not None:
            cur.execute(
                """
                SELECT id, doc_type, title, created_by_agent, supersedes_id, created_at
                FROM documents WHERE doc_type = %s
                ORDER BY created_at DESC LIMIT %s
                """,
                (doc_type, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, doc_type, title, created_by_agent, supersedes_id, created_at
                FROM documents ORDER BY created_at DESC LIMIT %s
                """,
                (limit,),
            )
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["created_at"] = d["created_at"].isoformat()
            results.append(d)
        return results

def get_related_documents(document_id: int) -> list[dict]:
    """Return every document linked to or from the given document, via
    document_links - both auto-created ('related_to', from
    auto_link_similar_documents) and manually-created edges (e.g.
    supersedes, contradicts, informed_by).

    Each result includes the related document's id/title/doc_type, the
    relation, and direction ('outgoing' if this document points to it,
    'incoming' if it points to this document). Does not include content -
    use get_document for that.
    """
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT d.id, d.title, d.doc_type, l.relation, 'outgoing' AS direction
            FROM document_links l JOIN documents d ON d.id = l.to_doc_id
            WHERE l.from_doc_id = %s
            UNION ALL
            SELECT d.id, d.title, d.doc_type, l.relation, 'incoming' AS direction
            FROM document_links l JOIN documents d ON d.id = l.from_doc_id
            WHERE l.to_doc_id = %s
            """,
            (document_id, document_id),
        )
        return [dict(row) for row in cur.fetchall()]

def list_unembedded_documents() -> list[dict]:
    """Return every document that has no stored embedding yet - written
    before auto-linking existed, or where a prior auto_link_similar_documents
    call was skipped or failed before completing.

    Each returned id can be passed directly into auto_link_similar_documents
    to backfill it. Normally returns few or zero rows - a non-empty result
    means something to catch up on, not a broken system.
    """
    with _connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT d.id, d.title, d.doc_type, d.created_at
            FROM documents d
            LEFT JOIN document_embeddings e ON e.document_id = d.id
            WHERE e.document_id IS NULL
            ORDER BY d.created_at
            """
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            r = dict(row)
            r["created_at"] = r["created_at"].isoformat()
            results.append(r)
        return results

def auto_link_similar_documents(document_id: int, threshold: float = 0.85) -> dict:
    """Embed a document and compare it against all other documents' stored
    embeddings, creating a 'related_to' link (via link_documents) for any
    pair scoring above the cosine-similarity threshold (0-1, default 0.85).

    Call this once after writing a new document, passing its id. Backfills
    the document's own embedding first if it doesn't have one yet.
    Idempotent - re-running for the same document just re-checks and
    re-creates any missing links; existing links are never duplicated.
    Returns which document ids (if any) were newly linked.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT content FROM documents WHERE id = %s", (document_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No document with id {document_id}")
        content = row[0]

        cur.execute(
            "SELECT embedding FROM document_embeddings WHERE document_id = %s",
            (document_id,),
        )
        existing = cur.fetchone()
        if existing is None or existing[0] is None:
            embedding = openrouter._embed(content)
            cur.execute(
                """
                INSERT INTO document_embeddings (document_id, embedding)
                VALUES (%s, %s)
                ON CONFLICT (document_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                (document_id, embedding),
            )
            conn.commit()

        cur.execute(
            """
            SELECT document_id, 1 - (embedding <=> (
                SELECT embedding FROM document_embeddings WHERE document_id = %s
            )) AS similarity
            FROM document_embeddings
            WHERE document_id != %s AND embedding IS NOT NULL
            ORDER BY similarity DESC
            """,
            (document_id, document_id),
        )
        candidates = cur.fetchall()

        linked = []
        for other_id, similarity in candidates:
            if similarity < threshold:
                continue
            cur.execute(
                """
                INSERT INTO document_links (from_doc_id, to_doc_id, relation)
                VALUES (%s, %s, 'related_to')
                ON CONFLICT (from_doc_id, to_doc_id, relation) DO NOTHING
                RETURNING id
                """,
                (document_id, other_id),
            )
            if cur.fetchone() is not None:
                linked.append({"document_id": other_id, "similarity": round(float(similarity), 4)})
        conn.commit()

        return {"document_id": document_id, "newly_linked": linked, "candidates_checked": len(candidates)}
