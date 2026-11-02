# Document graph view and daily sync: implementation plan (HOR-8 D)

Status: planned, not implemented. Pipeline item 45, Decision 9 (accepted, Option C), Stage 1 assessment Document 31. The canonical plan is Document 34 in Drive; this note is its repo reference (first indexed as Document 32 in run R-22, since removed from the Document Index). Code read at `main` @ `efce2e1` (29/10/2026).

## Context

There is no visual way to see the document graph. The sync job (`review_tab.py`) rewrites the Entities and Entity types tabs, but those hold no document–entity or document–document links, and nothing runs the sync on a timer. The web app can't reach Neon or the MCP (no `script.external_request` scope; the MCP needs OAuth).

## Decision

- The sync job writes a third tab, **Graph links**, in the Document Index workbook next to the Entities tabs.
- The pipeline-decisions web app gets a read-only **Graph** view that reads that tab and draws it with Cytoscape.js. It opens on one domain, Pipeline item or entity and is capped at 500 nodes and 1,500 edges.
- The sync runs daily, first as a **Graph sync** scheduled agent through `horology-watcher-setup`. Cloud Scheduler is the fallback if routine runs prove unreliable.
- No new MCP tool, scope, credential or migration. Live views (Option D) and JDBC (Option E) stay rejected.

## Graph links tab

One tab, one row per node or edge, so the web app reads a single range. The job rewrites it on each run with `replace_tab`; edits in it are not read back.

| Column | Node rows | Edge rows |
|---|---|---|
| Kind | `document` or `entity` | `link`, `supersedes`, `mention` or `relation` |
| From ID | Node ID: `D<graph document id>` or `E<entity id>` | Source node ID |
| From name | Document title or entity name | Source name (for reading the tab by hand) |
| To ID | blank | Target node ID |
| To name | blank | Target name |
| Type | `doc_type`, or the entity's bucket | `document_links.relation`, `supersedes`, `mentions`, or the relation type name |
| Weight | Entity: documents that name it; document: blank | Mention: passages naming the entity; relation: evidence passages; link: blank |
| Domain | Document's domain; entity: blank | Domain of the document end (mention, link); blank for relations |
| Pipeline ID | Document's Pipeline ID | Same rule as Domain |
| Link | Drive URL for sheet documents; blank for agent documents | blank |

Header constant `GRAPH_HEADER` in `review_tab.py`. Only active entities and the workspace's documents are written. Edges whose ends aren't both written are dropped. Rows are sorted by Kind, then From ID, so a diff between runs reads cleanly.

Today the tab would be small: 59 entities, about ten graph documents. On 29/10/2026 only one Document Index row (14) shows `synced`; most rows have Graph Inclusion FALSE or blank, so they aren't in the graph or the view (see open questions).

## Changes by file

**Document graph core (`document-graph-core/graph_core/`)**

- `documents/repository.py`: `graph_nodes(workspace)` (id, title, doc_type, source, domain, pipeline_id, drive_url, supersedes_id) and `graph_links(workspace)` (from, to, relation from `document_links`, both ends in the workspace). One query each.
- `entities/repository.py`: `mention_pairs(workspace)` (entity, document, count of mention passages, active entities only) and `relation_rows(workspace)` (from, relation type name, to, evidence count).
- `documents/service.py` and `entities/service.py`: thin `graph_*` functions over those, following the existing service/repository split.

**Sync job (`jobs/document-graph-sync/graph_sync/review_tab.py`)**

- `GRAPH_TAB = "Graph links"`, `GRAPH_HEADER`, `GRAPH_ROW_LIMIT = 20_000`.
- `write_graph_tab(google, spreadsheet_id, workspace)`: create the tab if missing, build node rows then edge rows, and `replace_tab`. Over the limit, keep all node rows and the heaviest edges, log a warning, and return `{"rows": n, "truncated": k}`.
- `run()`: add a fourth contained step, `graph_links`, after `tab_rows`. It runs in both `sync` and `entities` modes (`__main__.run_workspace` already calls `review_tab.run` in both), and its failure leaves the other tabs as written.
- Update the module docstring.

**Web app (`google_appscript/pipeline-decisions/src/`)**

- `WebApp.js`: `webRegisterIds()` adds `DOCUMENTS_ID` through the existing `registerIdFrom(values, /document index/i)`.
- New `Graph.js`:
  - `getGraphOverview()` returns the scope choices (domains, Pipeline items and entities with their counts) and the tab's row count.
  - `getGraphView(scope)` reads the Graph links tab with `getDisplayValues`, checks `GRAPH_HEADER`, and returns only the scoped view.
  - A pure `graphView(rows, scope, limits)` does the filtering, so it can be tested offline. Domain: that domain's documents, their entities, and the links among them. Pipeline item: its documents, their entities and the documents linked to them (one hop). Entity: the entity, the documents that name it and related entities.
  - Over the cap, nodes are ranked by degree and the view returns `truncated` with totals.
  - A missing tab returns an empty view with "Run the document-graph sync first".
- `Review.html`: a **Graph** nav button and `renderGraph()`. It has a scope picker (Domain, Pipeline item, Entity), a Cytoscape canvas using the built-in `cose` layout, a legend (documents by doc type, entities by bucket) and a side panel. Clicking a node shows its name, type, Pipeline ID and Drive link. Under the canvas, a node list keeps the view usable without the canvas. A truncation line reads "Showing 500 of N nodes; narrow the view."
- Cytoscape.js loads lazily the first time Graph opens, from cdnjs, pinned to an exact version with an SRI hash. If the HtmlService IFRAME blocks it, vendor the minified file as an HTML fragment through `shared-ui/build.mjs` (about 0.3 MB; Review.html is about 78 KB today).
- `appsscript.json`: unchanged. `SpreadsheetApp.openById` is already covered by the `spreadsheets` scope.

**Docs (same change)**

- `docs/architecture/mcp/document-graph.md`: sync step 4 also writes Graph links.
- `docs/architecture/subscription-agents/apps-script.md`: the Graph view.
- `docs/architecture/subscription-agents/workspace-records.md`: Document Index tabs.
- `docs/runbook/mcp/document_graph_server.md`: the daily schedule and how to pause it.
- Add a dated implementation note when it ships.

## Payload limits

- The server returns only the scoped view: at most 500 nodes and 1,500 edges, roughly 150–250 KB of JSON. It never returns the whole tab. The `google.script.run` limit isn't documented, so the cap stays server-side.
- Reading a 20,000-row by 10-column tab (200k cells) is well within Apps Script's 6-minute limit, but its time is untested. No CacheService at first: its 100 KB per-key limit is below a capped view.
- Cytoscape interaction slows at around 2,000 elements, and 500 + 1,500 sits at that edge. If dragging is slow, lower the edge cap first.
- The job's 20,000-row cap keeps the tab far below the 10M-cell workbook limit.

## Daily sync

1. Run `horology-watcher-setup` and choose type **Graph sync**: Claude routine, daily at a few minutes past the hour (proposed 05:07 Asia/Singapore, before the digest), with only the document-graph connector. Its prompt is the skill's Graph sync prompt. Record it on the Agent Register's Watchers tab; the skill does that.
2. Each run calls `sync_graph` once. The job chains up to `MAX_CHAIN` (10) follow-up runs of 30 changed documents itself. The 5-minute cooldown doesn't affect a daily run. Unchanged documents make no embedding calls.
3. Check after a week: `list_runs`/the sync history shows one run a day without failures, and Entities rows age out of `new`.
4. Fallback, only if routine runs prove unreliable: a Cloud Scheduler HTTP job calls the Cloud Run Admin API `jobs/<GRAPH_SYNC_JOB>:run`. It uses a service account with `roles/run.invoker` on that job, in the job's region. That is an infrastructure change with its own runbook section. Pause the routine when it goes live so the two don't overlap (the job's run claim would skip the second anyway).

## Tests

- Unit `tests/unit/jobs/test_graph_links_tab.py`: header, node and edge rows from fake service results, `D`/`E` ID prefixes, dropped orphan edges, the row cap and truncation count, and a failing graph step leaving `run()` summary `"failed"` for that step only.
- Integration `tests/integration/document_graph_core/test_graph_rows_postgres.py`: the four queries on disposable PostgreSQL. Covers workspace isolation, merged entities excluded, and mention counts. Extend `tests/integration/jobs/test_review_tabs.py` so the third tab is written.
- Apps Script `google_appscript/pipeline-decisions/tests/test-graph.cjs`, added to `npm test`. Covers missing tab, wrong header, each scope, one-hop neighbours, caps and the truncation message, and agent documents without a link.
- Run `.venv/bin/python -m pytest tests/unit -q`, the integration tests above, and `npm test` in `google_appscript/pipeline-decisions`.

## Rollout

1. Optional, founder: merge duplicate entities (Pillow, PyJWT, linkify-it, vite, Twitter and Twitter/X) through the Entities tab, so the first picture is clean.
2. Merge the code. Release the sync job image through the existing Cloud Build pipeline, run `sync_graph` once, and check the Graph links tab.
3. `npm run clasp:push`, then deploy a new web-app version. Open Graph, filter by a domain, a Pipeline item and an entity. Then paste a synthetic 5,000-row tab into a copy of the workbook to check the payload and the cap message.
4. Set up the Graph sync scheduled agent (above).

## Rollback

- Web app: redeploy the previous web-app version. The tab is harmless without the view.
- Sync job: roll back to the previous image. The Graph links tab then just stops refreshing; delete it by hand if wanted. Nothing else reads it.
- Schedule: pause or remove the routine with `horology-watcher-setup`, which also updates the Watchers row.
- No data migration, so there's nothing to undo in Neon.

## Open questions

- Is daily freshness enough? A live view is Option D, at High effort.
- Should agent-written documents appear? Proposed: yes, marked as agent documents, without a Drive link.
- Graph Inclusion: most Document Index rows are FALSE or blank, so the view starts nearly empty. Which rows should the founder turn on before rollout?
- Should the Graph view link to the Pipeline item view for a document's Pipeline ID? Proposed: yes, if the Pipeline item view can be opened by ID.
- Does the cdnjs load work inside the web app's IFRAME? This decides CDN versus vendoring and is the first thing to try.
