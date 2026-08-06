# Research Brief

## Topic
- document-linking-approach

## Question
- Documents in the document graph weren't getting linked to each other — no agent had reliably called `link_documents`, and prompting agents to do it consistently seemed likely to cost tokens/turns without guaranteeing compliance. What's the right fix: plain text/keyword search, embeddings, a hybrid of both — and how should the linking logic actually run (a script, a new service/framework, or something else)?

## Summary
- The actual failure case (two GTM documents addressing the same question with almost no shared vocabulary) is a semantic-similarity problem, not a keyword-matching one — plain text search wouldn't have caught it either, so it wasn't worth building first.
- Embeddings solve this directly. Given the corpus is tiny (a handful of documents, growing slowly) and Gemini embeddings are near-free at this volume (per earlier research), going straight to embeddings was the right call — no need to stage "text search now, embeddings later."
- Hybrid (text + embeddings) is a legitimate pattern at real scale but premature complexity here.
- No new framework (FastAPI or similar) is needed — this is a background job with no external caller, not something that needs to expose HTTP endpoints to anything.
- The cleanest execution shape: a new tool on the *existing* document-graph MCP server, triggered by agent personas immediately after `write_document`, rather than a separate service, script, or scheduled sweep.

## Sources
- Direct inspection of the document graph's actual state (3 documents, 1 manual link) before deciding anything.
- Earlier session research on Gemini embeddings cost/latency (`2026-08-06`, embeddings-vs-Modal comparison).
- Live verification of OpenRouter's embeddings API (see the `openrouter-embeddings-for-gemini` finding folded into the implementation note, since it was discovered mid-build rather than as a separate research question).

## Findings
- Reviewed the actual failing example (two GTM recommendations reaching different conclusions to the same question) before choosing an approach — this concretely showed keyword overlap would be near-zero between the two, ruling out text search as a fix for the real problem.
- FastAPI (or any web framework) would add infrastructure with no consumer — the job needs to run and do its work, not be called by anything external.
- Considered three trigger mechanisms: (a) a new tool on the existing document-graph MCP server, called by agents right after writing; (b) a standalone script + host/Hermes cron, decoupled from the write flow; (c) a periodic backfill sweep. Chose (a): reuses the container/credential already built, keeps linking tied to the moment a document is created (matching current low volume, where a delayed batch sweep adds latency for no benefit), and needed no new service.

## Recommendation
- Build `auto_link_similar_documents` as a new tool on `document-graph-mcp`, not a separate service.
- Skip text/keyword search entirely for this use case; go straight to embeddings.
- Revisit hybrid search only if/when document volume and query patterns actually demand it — not a near-term concern.

## Open Questions
- None outstanding for the approach itself — implementation specifics (embedding provider, dimension count, index type) are covered in the corresponding implementation note, including two assumptions that turned out wrong and were caught by testing rather than trusted from documentation.
