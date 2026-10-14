# document-graph-core

Document graph logic shared by the document-graph MCP service (`mcp-servers/document-graph/`) and its sync job (`jobs/document-graph-sync/`). The gateway does not use it. Infrastructure shared by every service (database pool, sign-in, settings, logging, reference data) stays in `shared-runtime/`.

Organised by domain. Each domain has a `service.py` (logic) and a `repository.py` (that domain's SQL only):

| Domain | Owns |
|---|---|
| `documents/` | document rows, document-to-document links, sheet bookkeeping |
| `sections/` | chunking, section and document embeddings, passage search, nearest documents |
| `topics/` | the section-similarity graph, Louvain clustering, topic names, placement of new sections, topic lookups |
| `providers/` | outside APIs wrapped once: OpenRouter embeddings and the JSON chat model (`GRAPH_LLM_MODEL`, default `google/gemini-3.1-flash-lite`). IP addresses are masked before any text leaves (`masking.py`); stored text is unchanged. |

Rules:
- Entry points (MCP tools, the job) call services.
- Domains call each other's services, never each other's repositories.
- Repositories may JOIN `documents` to scope by workspace or show titles; only `documents/` writes it.

Bind the shared pool once with `graph_core.configure(database)` (the server's lifespan and the job's `main` do this).

Install for development: `pip install -e ./document-graph-core` (with `./shared-runtime`).
