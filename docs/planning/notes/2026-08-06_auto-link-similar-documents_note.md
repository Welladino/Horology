# Implementation Note

## Topic
- auto-link-similar-documents

## Context

Approach decision (embeddings over text search, MCP tool over a new service) is in [`docs/planning/research/2026-08-06_document-linking-approach_research.md`](../research/2026-08-06_document-linking-approach_research.md). This note covers what was actually built, including two assumptions that turned out wrong and were caught by live testing before they became load-bearing mistakes.

## Decision

**Added `document_embeddings` table** (Alembic migration `20260806_001`): `document_id` (FK to `documents`, cascade delete), `embedding vector(768)`, `created_at`. HNSW cosine-similarity index, built outside a transaction — same pattern as `Article_aggregator_agent`'s own pgvector migrations (extension enable, HNSW built via `autocommit_block()`), reused without importing that project's code.

**Added `auto_link_similar_documents(document_id, threshold=0.85)`** as a fourth (well, fifth) tool on `document-graph-mcp`: embeds the given document if it has no stored embedding yet, compares it via cosine similarity against every other document's stored embedding, and creates a `related_to` edge (via the same `link_documents` insert logic) for any pair scoring above the threshold. Idempotent — safe to call more than once for the same document.

**Embedding provider: OpenRouter, not a direct Gemini/GCP key.** The founder was about to provision a separate Google AI Studio/GCP key and asked whether to instead reuse the existing OpenRouter key — checked and confirmed: OpenRouter has a real `/v1/embeddings` endpoint (OpenAI-compatible shape) proxying `google/gemini-embedding-001`, so the existing OpenRouter key (already used for Hermes's chat models) works for this too. No new GCP project, key, or IAM setup needed. The key is duplicated into the root `.env` (for `document-graph-mcp`'s own container environment) rather than mounting `hermes-data/.env` into that container, keeping the "each MCP server holds its own credential, never shares Hermes's environment" pattern intact.

**Two assumptions were wrong and caught by live testing, not by trusting documentation:**

1. **Assumed 768-dim output by default** (matching Gemini's native API default, and `Article_aggregator_agent`'s own `vector(768)` column). A live test call returned **3072 dimensions**. This would have silently broken the migration's `vector(768)` column (or produced a dimension mismatch error on insert) if not caught before real use.
2. **3072 dims exceeds pgvector's HNSW index limit (2000 dims)** — confirmed via web search after discovering (1). The original migration's `CREATE INDEX ... USING hnsw` would have failed outright once real (3072-dim) embeddings were inserted.
3. **Fix, also verified live rather than assumed impossible:** OpenRouter's embeddings docs don't mention a `dimensions` parameter, and earlier research concluded Gemini-specific params "are not passed through" — but a direct test call with `"dimensions": 768` in the request body returned exactly 768 dimensions. OpenRouter passes it through to Gemini's native `output_dimensionality` even though it's undocumented on their side. Used this to keep the original `vector(768)` schema (avoiding a `halfvec` migration) by having the server explicitly request 768 dims on every embed call (`EMBED_DIMENSIONS = 768` constant in `server.py`, sent as `"dimensions": EMBED_DIMENSIONS`).

**Verified end-to-end, not just unit-tested:**
- Ran `auto_link_similar_documents` for document 6 first — correctly found `candidates_checked: 0` (documents 5 and 7 pre-dated this tool and had no embeddings yet), stored document 6's own embedding.
- Ran it for documents 5 and 7 (backfilling their embeddings in the process) — document 5 correctly matched document 6 at 0.857 cosine similarity (above the 0.85 threshold) and created a `related_to` link; document 7 (an unrelated GitHub repo health report) correctly matched neither at that threshold, no spurious link created.
- Confirmed the new link directly via SQL query against `document_links`, not just the tool's own reported success.

**All four personas updated** (Second-Soul + three subagents) to call `auto_link_similar_documents` with the new document's id immediately after every `write_document` call — verified via a live query that Second-Soul correctly describes this as its own next step after writing.

## Rationale

Every step followed the project's standing practice: verify a claim (dimension count, whether `dimensions` is honored) with a real call before writing code or schema against an assumption, especially when the assumption is about to become load-bearing (a fixed-width Postgres column, an index type with a hard limit). Both wrong assumptions here were the kind that fail *silently or much later* — a dimension mismatch or an HNSW build failure discovered only once real documents were being written — rather than obviously at setup time, which is exactly the category of mistake worth testing for deliberately.

## Impact

- `document_embeddings` is now a real, populated table (documents 5, 6, 7 all have stored embeddings as of this note).
- `document_links` has grown from 1 manually-created edge to 2 (the original plus the new auto-created one) — the auto-linking mechanism is live, not just built.
- Every future `write_document` call from any persona is followed by an automatic similarity check — the founder's original problem (documents never getting linked because no one reliably remembered to call `link_documents`) is now structurally addressed, not dependent on agent diligence.

## Follow-Ups

- No backfill sweep exists for documents that predate this feature and are never touched again — the three existing documents got their embeddings only because they were manually re-processed during testing. If older, untouched documents matter later, a one-time backfill script (or a periodic sweep, considered and set aside in the research brief) would be needed.
- `EMBED_DIMENSIONS = 768` and the `dimensions` parameter's undocumented behavior on OpenRouter should be re-verified if OpenRouter or the underlying Gemini model version changes — this is relying on unofficial pass-through behavior, not a documented contract.
- Threshold (0.85) was accepted at its stated default, not tuned against real data — worth revisiting once there are enough documents to judge whether it's producing false positives/negatives.
