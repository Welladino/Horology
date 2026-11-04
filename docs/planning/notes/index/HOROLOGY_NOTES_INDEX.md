# Horology Notes Index

Implementation notes under `docs/planning/notes/`, grouped by area. Add a row when a new note is created.

## Foundations

| Date | Note | Covers |
|------|------|--------|
| 2026-08-05 | [Founding decisions](../2026-08-05_horology-founding-decisions_note.md) | Why Hermes, the supervisor and subagent design, document storage |
| 2026-08-06 | [Test suite and dependency audit](../2026-08-06_test-suite-and-dependency-audit_note.md) | Unit and container tests, pip-audit, host isolation |

## Hermes

| Date | Note | Covers |
|------|------|--------|
| 2026-08-05 | [Kanban dispatch](../2026-08-05_hermes-kanban-dispatch_note.md) | The delegate_task truncation bug, kanban profiles, turn budgets and timeouts |
| 2026-08-05 | [Profiles and tools](../2026-08-05_hermes-profiles-and-tools_note.md) | Personas in the repo, the subagent index, skills and tools per profile |
| 2026-08-05 | [Hardening](../2026-08-05_hermes-hardening_note.md) | Localhost ports, egress firewall, toolset trimming, filesystem isolation |

## Subscription agents

| Date | Note | Covers |
|------|------|--------|
| 2026-10-10 | [Setup](../2026-10-10_subscription-agents-setup_note.md) | Apps Script under version control, naming, skills, prompts, repository layout |
| 2026-10-13 | [ClickUp eligible-row batching](../2026-10-13_clickup-eligible-batching_note.md) | Which Pipeline rows the sync processes, and in what order |
| 2026-10-17 | [Claude skills and connectors on claude.ai](../2026-10-17_claude-skills-and-connectors-on-claude-ai_note.md) | Why Claude uses claude.ai skills and connectors instead of plugins; the skill zip build |
| 2026-10-19 | [Pipeline Locations tab](../2026-10-19_pipeline-locations-tab_note.md) | Agent Location Directory Doc replaced by a sheet tab; v1.2 folder provisioning dropped |
| 2026-10-19 | [Folders, skills and Apps Script](../2026-10-19_folders-skills-and-apps-script_note.md) | Folder-only Locations, Domains tab, guide-free skills, bound decisions and Locations scripts, standalone ClickUp Sync |
| 2026-10-22 | [Completed status and ClickUp comments](../2026-10-22_completed-and-clickup-comments_note.md) | Final status without ClickUp closure, comment preview and workspace links |
| 2026-10-29 | [ClickUp shared tasks and onChange](../2026-10-29_clickup-shared-tasks-and-onchange_note.md) | Several items per ClickUp task, first-sync intro, Pipeline onChange trigger and lock |
| 2026-10-29 | [Implementation route](../2026-10-29_implementation-route_note.md) | Type chooses the route; Feature/Enhancement/Refactor/Fix plan at Stage 1 and implement at Stage 3, In progress, Completed or Implementation question (HOR-12 a) |
| 2026-10-29 | [Web workspace scale and usability](../2026-10-29_web-workspace-scale-and-ux_note.md) | Light lists with details on open, a 60-second list cache, embedded first list, hash navigation, search, chips, sort and paging (HOR-12 c) |
| 2026-10-30 | [Web workspace Triage board](../2026-10-30_web-workspace-triage-board_note.md) | Dark top bar, decisions inbox with reading pane, Pipeline board by workflow column, Build/Investigate Type filter (HOR-12 c, item 52) |
| 2026-11-03 | [Web item quick edit](../2026-11-03_web-item-quick-edit_note.md) | Numbered steps kept with their marker, Agent and domain quick edit on the item page, Domain and Entity validation (HOR-15, item 65) |
| 2026-11-02 | [Drive-first agent documents](../2026-11-02_drive-first-agent-documents_note.md) | Every deliverable in Drive with the template the agent chooses; repo docs only where a repository keeps its own, on the item's branch; ClickUp sync accepts Drive links only |
| 2026-11-03 | [Stage 4 items end Completed](../2026-11-03_stage-4-completed_note.md) | Synthesis saved means Completed at Stage 4; a proposed Specialist deliverable decision stays open to keep or reopen the item (HOR-14, item 67, Decision 15) |
| 2026-11-04 | [Drive-only Research Links](../2026-11-04_drive-only-research-links_note.md) | Decision Register Research Links holds Drive files only; `check_register_write` refuses other links; Decisions 13 and 14 relinked to Drive documents (HOR-9, item 68) |
| 2026-11-04 | [Pages tab for published pages](../2026-11-04_pages-tab_note.md) | Document Index Pages tab lists every Cloudflare page; the publishing skill adds the row after a verified publish; backfill of items 39 and 45 (item 70, HOR-9) |
| 2026-11-04 | [Stage 1 document and Implementation report](../2026-11-04_stage-1-document-and-implementation-report_note.md) | Every route writes a Stage 1 Drive document plus Steps rows; the implementation route writes an Implementation report and a Stage 4 page and ends Completed at Stage 4; Graph Inclusion stays the founder's (item 69, HOR-9) |

## MCP gateway

| Date | Note | Covers |
|------|------|--------|
| 2026-10-11 | [Gateway and shared runtime](../2026-10-11_mcp-gateway-and-shared-runtime_note.md) | One gateway, Neon quota ledger, shared runtime, logging and errors |
| 2026-10-11 | [Supabase TLS](../2026-10-11_gateway-supabase-tls_note.md) | The official public CA, packaged in the image |
| 2026-10-12 | [Provider scope](../2026-10-12_gateway-provider-scope_note.md) | Alexandria and extraction added, GitHub and Google removed, public HTTPS scraping |
| 2026-10-13 | [Shared policy and budgets](../2026-10-13_gateway-shared-policy-and-budgets_note.md) | No assignments, Audience sign-in, baked policy, daily and monthly caps |
| 2026-11-04 | [Multi-page Pages publishing](../2026-11-04_multipage-pages-publishing_note.md) | Extra HTML, JS and JSON files, page-named branches, Access unchanged |

## Document graph

| Date | Note | Covers |
|------|------|--------|
| 2026-08-06 | [First version](../2026-08-06_document-graph-v1_note.md) | Server, embeddings, auto-linking, embedding sweep, near-duplicate threshold |
| 2026-10-13 | [Workspaces, sign-in and sync](../2026-10-13_document-graph-workspaces-signin-and-sync_note.md) | Workspaces, shared sign-in, the Document Index sync job |
| 2026-10-14 | [Passage search](../2026-10-14_document-graph-passage-search_note.md) | Section-by-section search with matching passages |
| 2026-10-29 | [Register ID allocator](../2026-10-29_register-id-allocator_note.md) | Atomic Decision/Document IDs, ownership check before register writes, rows found by ID (HOR-6) |
| 2026-10-29 | [Text-based agent documents](../2026-10-29_text-based-agent-documents_note.md) | No images in agent Docs, visuals in Stage 4 synthesis, TA ratings table replaces quadrant (HOR-11 rejected) |
| 2026-10-29 | [Structured decisions and revise](../2026-10-29_structured-decisions-and-revise_note.md) | Options and Steps tabs, option cards on the decision page, revising a decided decision (HOR-8 A+B) |
| 2026-10-29 | [Document graph view and daily sync (plan)](../2026-10-29_document-graph-visual-view_note.md) | Graph links tab from the sync job, read-only Cytoscape.js Graph view, daily Graph sync schedule (HOR-8 D, Decision 9; not yet implemented) |

## Cloud, data and local infrastructure

| Date | Note | Covers |
|------|------|--------|
| 2026-10-11 | [Cloud Run deployment and OAuth](../2026-10-11_cloud-run-deployment-and-oauth_note.md) | Region, first deployment, Google-backed MCP sign-in, consent fix |
| 2026-10-12 | [Release pipeline and access](../2026-10-12_release-pipeline-and-access_note.md) | Cloud Build gates, image retention, deployer impersonation, free-tier builds |
| 2026-10-12 | [Local Compose projects](../2026-10-12_local-compose-projects_note.md) | Three independent Docker projects, localhost ports |
| 2026-10-13 | [Psycopg 3 and round trips](../2026-10-13_psycopg3-and-database-round-trips_note.md) | One driver, token cache, login defaults, single-trip queries |
