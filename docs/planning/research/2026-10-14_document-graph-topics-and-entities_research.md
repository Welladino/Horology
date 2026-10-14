# Research Brief

## Topic
- document-graph-topics-and-entities

## Question
- **The gap:** the document graph links documents to documents (similar, supersedes, named links) and searches passages by meaning. It can't give agents:
  - an overview of themes;
  - complete lists, such as every platform we evaluated;
  - "everything about X" under any spelling;
  - facts linking things, such as "Beehiiv competes with Substack".
- **The question:** how should we add topic and entity layers, cheaply and in a way that grows with the corpus? And where does the shared code live?

## Summary
- **Topics come from the embeddings we already have.** Link each section to its ~10 most similar sections, cluster the graph with NetworkX Louvain plus a connected-pieces fix, then name the clusters with Gemini Flash Lite.
- **Entities come from an LLM:**
  1. extract mentions into a fixed set of about 10 buckets;
  2. resolve them: an exact match after lowercasing, then an embedding shortlist of 5 candidates in the same bucket;
  3. let Flash Lite judge "same or new";
  4. you review the results in an Entities tab.
- **Shared code moves into one package.** Graph logic used by both the MCP service and the sync job leaves the MCP server folder. Reference data used by several services (ISO countries) moves into `shared-runtime`.

## Sources
- **GLiNER v2.1 models:** small 166M, medium 209M, large 459M parameters; Apache 2.0 (v0/v1 are non-commercial). [pypi](https://pypi.org/project/gliner), [model listings](https://telemetry.superlinked.com/models/urchade-gliner_large-v2-1.md)
- **GLiREL:** ~435–467M parameters, licence unconfirmed. [arXiv 2501.03172](https://arxiv.org/abs/2501.03172v1)
- **Jev (TypeSafe AI):** a non-generative decision model, early access since 2026-09-15, about $0.042 per million input tokens. [Neo4j](https://neo4j.com/?p=432101), [review](https://wavect.io/es/blog/jev-ai-decision-model-review/)
- **Leiden:**
  - NetworkX's `leiden_communities` needs a backend (GPU-only nx-cugraph). [docs](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.leiden.leiden_communities.html)
  - `leidenalg` is GPL.
  - `graspologic-native` is MIT, but has only old documented wheels. [pypi](https://pypi.org/project/graspologic-native/1.1.1/)
- **NetworkX 3.7:** 2.1 MB wheel, 8.1 MB installed, no required dependencies, BSD licence. Louvain is 362 lines (measured 2026-10-14).
- **Wikidata quality:** the main problems are duplicates, missing facts and type violations; factual accuracy is under-studied. [Shenoy et al.](https://arxiv.org/abs/2107.00156v4)
- **Entity linking with ReFinED:** 92.1 micro F1 on Wikidata; no published score for company names. [ReFinED](https://arxiv.org/pdf/2207.04108)

## Findings

### Topics
- **Topic nodes and entity nodes answer different questions.**
  - **Topics** answer "what themes exist, and what belongs together". They come from grouping embeddings, with no extraction.
  - **Entities** answer "everything about X" and record relationships. They need extraction.
- **Graph nodes are sections.** Each section links to its ~10 nearest sections, and the 10 sets how connected the graph is, not how many sections are clustered. Building the graph grows roughly linearly with sections.
- **Agglomerative clustering grows quadratically** and becomes impractical at around 50k sections.
- **Louvain's flaw:** it can leave a community whose sections aren't linked to each other. Splitting each community into its connected pieces fixes that.
- **Keep runs stable:**
  - a fixed seed makes runs repeatable;
  - matching new topics to old ones through shared sections keeps names stable;
  - between re-clusters, a new section joins the topic of its nearest neighbours.

### Entities
- **Buckets alone aren't enough.** They group kinds of thing (Kit and Beehiiv are both *platform*), but answering "everything about Beehiiv" needs distinct entities inside each bucket. Those are separate jobs:
  - **identity:** SG, sg and Singapore are one thing;
  - **bucket:** Kit and Beehiiv are both platforms, but different ones.
- **Similarity alone can't resolve names:**
  - competitors look alike: Substack and Beehiiv can score around 0.9;
  - renames look different: Kit and ConvertKit may score around 0.7.

  A judge is needed in between. The shortlist keeps judge prompts the same size as entities grow, and tends to improve accuracy.
- **Bucket changes are mostly cheap.** Renames and merges are instant. Splits, and promoting `other` suggestions, only re-sort entities. Only new kinds of thing need re-extraction.
- **Wikidata and data APIs** (e.g. Parallel) suit public names only, for linking or enrichment. Internal names must not be sent to them.

### Document fields
- **Domain, Entity and Pipeline ID** from the Document Index can be stamped on graph documents during sync.
- **Sheet edits must still reach the graph.** Metadata-only edits don't change the Drive revision, so unchanged rows still need a cheap metadata update.
- **Domain spelling** differs between the Pipeline and the Document Index, so the graph stores one normal form.

### Code layout
- **The sync job currently imports the MCP server's package** for chunking, embedding and repositories. Those are shared by two services, so they belong in a shared package, not in either service.
- **ISO country codes are used by the gateway** and, under this plan, by entity normalisation. That makes them reference data for `shared-runtime`.

## Recommendation

### Build order
1. **Document fields:** `domain`, `business_entity` (the sheet's "Entity", renamed so it isn't confused with entity nodes) and `pipeline_id` on documents. Stamped by the sync, refreshed without re-embedding, with domain filters on the tools.
2. **Topic graph:**
   - section links, Louvain plus the fix, and Flash Lite naming;
   - incremental placement during sync, and re-clustering on demand (`rebuild_topics`, a job mode);
   - `list_topics` / `get_topic`.
3. **Entities:**
   - extract, exact match, embedding shortlist, then a Flash Lite judge, with a decision log;
   - Entities and Entity types tabs;
   - `find_entity` / `entity_documents`;
   - incremental processing by section content hash, with `pending` on failure.
4. **Sync cooldown:** a 5-minute window per workspace for `sync_graph` and `rebuild_topics`.
5. **Deploy everything together,** then build the first topics and entities.

### Rules
- Everything is scoped by workspace.
- Agents only ever receive text.
- Topics and entities never block search.

### Code layout (agreed 2026-10-14)

**Import rules:**
- Services never import each other.
- Logic used by two or more programs goes into a shared package.
- Reference data used across services goes into `shared-runtime`.
- Code used by only one program stays with it. Google Drive/Sheets access stays in the job; starting the Cloud Run job stays in the MCP service.

**The shared package** is `document-graph-core` (package `graph_core`). It's used by the document-graph MCP service and its sync job. The gateway doesn't use it. It's organised by domain:

| Domain | Owns |
|---|---|
| `documents/` | document records, fields (domain normal form, `business_entity`, `pipeline_id`), document links |
| `sections/` | chunking, section embeddings, passage search, nearest neighbours |
| `topics/` | neighbour graph, Louvain plus fix, naming, placement, topic lookups |
| `entities/` | buckets, prompts, extraction, resolution, entity lookups, re-bucketing |
| `runs/` | sync and topic run requests (the cooldown) |
| `providers/` | outside APIs wrapped once: OpenRouter embeddings and the Flash Lite chat client |

**Structure rules:**
- Each domain has a `service.py` (logic) and a `repository.py` (that domain's SQL only).
- Domains call each other's services, never each other's repositories.
- Dependencies point one way: entry points, then services, then repositories and providers.

**Kept deliberately simple:** plain modules and functions; no model classes, abstract repository interfaces or plugin system.

**Entry points stay thin:**
- **The MCP tools** validate input, take the signed-in workspace and call a service.
- **The job** orchestrates: rows, then services.

**`shared-runtime/horology_runtime/reference/countries.py`** holds the ISO 3166 list, used by the gateway's trends and Shopify tools and by entity normalisation.

### Decided
- **Agent documents** are embedded, linked and placed in topics immediately by the service. Their entities are extracted by the job's next run, so agents never wait on LLM calls.
- **The Entities and Entity types tabs** live in the Document Index workbook.
- **Models:** Gemini Flash Lite via OpenRouter, for naming, extraction and judging.

## Open Questions
- Topic resolution and the neighbour count (k): tune on real data.
- The entity judge's confidence threshold for auto-merging versus review.
- Later candidates: Jev as the judge; Wikidata linking for public names; Parallel-style enrichment; true Leiden if a supported wheel exists.
