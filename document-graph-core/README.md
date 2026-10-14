# document-graph-core

Document graph logic shared by the document-graph MCP service (`mcp-servers/document-graph/`) and its sync job (`jobs/document-graph-sync/`). The gateway does not use it. Infrastructure shared by every service (database pool, sign-in, settings, logging, reference data) stays in `shared-runtime/`.

Organised by domain. Each domain has a `service.py` (logic) and a `repository.py` (that domain's SQL only):

| Domain | Owns |
|---|---|
| `documents/` | document rows, document-to-document links, sheet bookkeeping |
| `sections/` | chunking, section and document embeddings, passage search, nearest documents. A document over 30 sections (about 20 pages) is rejected whole before anything is stored or sent (`TooLong`): `write_document` replies `saved: false`, and the sync marks the row `too_long`. |
| `topics/` | the section-similarity graph, Louvain clustering, topic names, placement of new sections, topic lookups |
| `entities/` | buckets and relationship types, extraction, resolution (exact match, embedding shortlist, LLM judge), review edits, entity lookups |
| `runs/` | sync-job runs: one at a time per workspace (`graph_runs`; the claim is taken when a request is accepted and confirmed by the job with a token, so nothing starts in between), a 5-minute cooldown on agent requests, starting the job through the Cloud Run API, and follow-up runs when a run's cap (30 documents for sync and entities) leaves work over, at most 10 in a row |
| `ai/` | chat and embeddings, wrapped once. Domains call `ai.chat` and `ai.embeddings`; the backend is a setting (`GRAPH_AI_BACKEND`, default `openrouter/`; `vertex/` is a placeholder). Models: `GRAPH_LLM_MODEL` (default `google/gemini-2.5-flash-lite`), `GRAPH_JUDGE_MODEL` for entity matching (default `google/gemini-2.5-flash`). `retry.py` retries timeouts, 429s and 5xx up to twice and logs each retry. `gate.py` allows at most 3 AI requests at once per process, so callers can work in parallel. IP addresses are masked before any text leaves (`masking.py`); stored text is unchanged. |

Rules:
- Entry points (MCP tools, the job) call services.
- Domains call each other's services, never each other's repositories.
- Repositories may JOIN `documents` to scope by workspace or show titles; only `documents/` writes it.

Bind the shared pool once with `graph_core.configure(database)` (the server's lifespan and the job's `main` do this).

Install for development: `pip install -e ./document-graph-core` (with `./shared-runtime`).
