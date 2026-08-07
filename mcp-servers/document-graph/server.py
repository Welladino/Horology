"""MCP server exposing operations against Horology's document graph
(documents / document_links / document_embeddings / run_log on Neon
Postgres), plus embedding-based auto-linking of similar documents.

No arbitrary SQL is exposed to callers. Every tool runs one fixed,
parameterized query. The DB connection string lives only in this process's
environment (DATABASE_URL_POOLED) - callers never see it. Embeddings go
through OpenRouter (reusing the same key Hermes uses for chat - OpenRouter
proxies google/gemini-embedding-001 via an OpenAI-compatible /v1/embeddings
endpoint), not a separate Gemini/GCP key - see
docs/planning/notes/2026-08-06_auto-link-similar-documents_note.md.
"""
import os

import httpx
import psycopg2
import psycopg2.extras
from mcp.server.mcpserver import MCPServer

VALID_DOC_TYPES = ("recommendation", "content", "analysis", "report")

DATABASE_URL = os.environ.get("DATABASE_URL_POOLED")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL_POOLED is not set in this server's environment.")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "google/gemini-embedding-001")
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"

mcp = MCPServer("horology-document-graph")


def _connect():
    return psycopg2.connect(DATABASE_URL)


EMBED_DIMENSIONS = 768  # must match the document_embeddings.embedding column's vector(N) width


def _embed(text: str) -> list[float]:
    """Embed text via OpenRouter's OpenAI-compatible /v1/embeddings endpoint.
    Raises if OPENROUTER_API_KEY is unset or the request fails - callers
    should let this propagate as a tool error rather than silently skip
    auto-linking.

    `dimensions` is undocumented on OpenRouter's embeddings endpoint but
    verified working live (passed through to Gemini's native
    output_dimensionality) - the model's un-truncated output is 3072 dims,
    which exceeds pgvector's 2000-dim HNSW index limit, so this is required,
    not optional."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in this server's environment.")
    resp = httpx.post(
        OPENROUTER_EMBEDDINGS_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": EMBED_MODEL, "input": text, "dimensions": EMBED_DIMENSIONS},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
            embedding = _embed(content)
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


if __name__ == "__main__":
    # streamable-http, bound to 0.0.0.0 *inside this container only* - no
    # host port is published for this service (see docker-compose.yml), so
    # it's reachable exclusively from other containers on the same Docker
    # network, by service name. This avoids mounting the Docker socket into
    # Hermes's container just to reach this one via `docker exec`.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
