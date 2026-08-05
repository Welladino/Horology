"""MCP server exposing exactly four operations against Horology's document
graph (documents / document_links / run_log on Neon Postgres).

No arbitrary SQL is exposed to callers. Every tool runs one fixed,
parameterized query. The DB connection string lives only in this process's
environment (DATABASE_URL_POOLED) - callers never see it.
"""
import os

import psycopg2
import psycopg2.extras
from mcp.server.mcpserver import MCPServer

VALID_DOC_TYPES = ("recommendation", "content", "analysis", "report")

DATABASE_URL = os.environ.get("DATABASE_URL_POOLED")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL_POOLED is not set in this server's environment.")

mcp = MCPServer("horology-document-graph")


def _connect():
    return psycopg2.connect(DATABASE_URL)


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
