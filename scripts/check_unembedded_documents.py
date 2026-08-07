#!/usr/bin/env python3
"""Cron script (default/agent mode, gated by the wakeAgent contract) - checks
the document graph for documents with no stored embedding yet.

Connects with CRON_SWEEP_RO_DATABASE_URL - a dedicated, SELECT-only Postgres
role (see alembic/versions/20260807_001_add_readonly_role_for_cron_sweep.py),
not document-graph-mcp's own read-write credential. Hermes cron scripts do
not inherit Hermes-managed secrets by design, so this must be its own,
separately-provisioned env var - see
docs/planning/research/2026-08-07_cron-script-security-pattern_research.md.

wakeAgent contract (verified hands-on against the real hermes container,
2026-08-07 - the official docs left several details undocumented):
- A final stdout line of exactly {"wakeAgent": false} skips the agent
  entirely for this run - confirmed zero LLM turn, output file just notes
  "Script gate returned wakeAgent=false - agent skipped."
- Any other stdout (including {"wakeAgent": true} or its total absence)
  wakes the agent, and ALL of this script's stdout - including the gate
  line itself - is injected verbatim into the agent's prompt under a
  "## Script Output" heading. The gate line is not stripped, so print
  nothing after the id list that isn't meant to end up in the agent's
  context.

On the "found something" path, this prints a plain-text list (one id per
line) that the paired cron job's prompt instructs the agent to read and
act on by calling auto_link_similar_documents(id) for each - see
docs/planning/notes/2026-08-07_document-graph-completeness-punch-list_note.md.

Source under test: none yet - runs only inside the hermes container's own
Python (asyncpg is already present there; psycopg2 is not, so this uses
asyncpg specifically, unlike the psycopg2-based MCP server code).
"""
import asyncio
import json
import os
import sys

import asyncpg

DATABASE_URL = os.environ.get("CRON_SWEEP_RO_DATABASE_URL")


async def _fetch_unembedded() -> list[asyncpg.Record]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetch(
            """
            SELECT d.id, d.title, d.doc_type, d.created_at
            FROM documents d
            LEFT JOIN document_embeddings e ON e.document_id = d.id
            WHERE e.document_id IS NULL
            ORDER BY d.created_at
            """
        )
    finally:
        await conn.close()


def main() -> int:
    if not DATABASE_URL:
        # No stdout at all here reaches the agent either way - print to
        # stderr for visibility in `hermes cron runs`, and let the agent
        # run anyway (no wakeAgent:false line) so a real misconfiguration
        # surfaces as a visible cron delivery instead of a silent no-op.
        print("CRON_SWEEP_RO_DATABASE_URL is not set.", file=sys.stderr)
        return 1

    rows = asyncio.run(_fetch_unembedded())
    if not rows:
        print(json.dumps({"wakeAgent": False}))
        return 0

    print(f"{len(rows)} document(s) missing an embedding - call auto_link_similar_documents for each id below:")
    for row in rows:
        print(f"- id={row['id']} doc_type={row['doc_type']} title={row['title']!r} created_at={row['created_at'].isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
