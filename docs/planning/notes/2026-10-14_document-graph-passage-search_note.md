# Implementation Note

## Topic
- document-graph-passage-search

## Context
- **One fingerprint per document:** each document had a single embedding of its first 8,000 characters. Anything later in a long document couldn't be found by search.
- **Whole documents only:** search returned documents, never the matching part, so agents read whole documents to find one detail.

## Decision
- **Sections.** `document_graph/chunking.py` splits each document into sections of up to 2,000 characters:
  - whole paragraphs are kept together; a paragraph over the limit is cut at sentence ends;
  - a Markdown heading starts a new section once the current one has 900+ characters;
  - a section that continues mid-topic repeats the previous section's last ~200 characters;
  - at most 200 sections per document.
- **One embedding per section,** each prefixed with the document title. They're stored in `document_chunks` (Alembic `20261014_002`, HNSW cosine index). OpenRouter is asked for 32 sections per request; batching was verified live on 2026-10-14.
- **Document-level vector.** `document_embeddings` keeps one vector per document: the normalised mean of its sections, used by `auto_link_similar_documents`. Sections and that vector are replaced together, in one transaction.
- **Search.** `search_documents(query, limit=5, passages=2)` ranks sections, groups them by document (the best section decides the order), and returns up to 3 passages per document with section number and similarity.
- **Re-embedding.** A document counts as not yet embedded, in `list_unembedded_documents` and the sync job's change check, until it has sections. Existing documents are re-embedded by the release's sync and backfill steps.

## Rationale
- **Section size.** About 2,000 characters (~500 tokens) is small enough to point at one topic, and big enough to read as a passage on its own.
- **Why the mean vector.** Averaging section vectors makes auto-linking reflect the whole document, not its first 8,000 characters, without another API call. The 0.85 threshold is unchanged; watch for link quality after the release.
- **Cost.** Roughly 500 tokens per section at $0.15 per million tokens, so a 20-section document costs about $0.0015 to embed.

## Impact
- **Plugins:** `horology-document-graph` 0.2.0. Its skill tells agents to read passages before opening whole documents.
- **Not deployed:** release steps are in the [deployment runbook](../../runbook/gcp/mcp_deployment.md).
- **Tests:** chunking rules, batched embedding order, grouped search, and a real-Postgres test where a detail past character 8,000 is found and returned as the passage.

## Follow-Ups
- **Headings:** Google Docs are exported as plain text, which drops heading markers. Exporting as Markdown would let headings guide the cuts.
- **Other file types:** PDF, Slides, Sheets and images, discussed next.
