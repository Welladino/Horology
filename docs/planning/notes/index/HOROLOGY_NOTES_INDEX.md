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

## MCP gateway

| Date | Note | Covers |
|------|------|--------|
| 2026-10-11 | [Gateway and shared runtime](../2026-10-11_mcp-gateway-and-shared-runtime_note.md) | One gateway, Neon quota ledger, shared runtime, logging and errors |
| 2026-10-11 | [Supabase TLS](../2026-10-11_gateway-supabase-tls_note.md) | The official public CA, packaged in the image |
| 2026-10-12 | [Provider scope](../2026-10-12_gateway-provider-scope_note.md) | Alexandria and extraction added, GitHub and Google removed, public HTTPS scraping |
| 2026-10-13 | [Shared policy and budgets](../2026-10-13_gateway-shared-policy-and-budgets_note.md) | No assignments, Audience sign-in, baked policy, daily and monthly caps |

## Document graph

| Date | Note | Covers |
|------|------|--------|
| 2026-08-06 | [First version](../2026-08-06_document-graph-v1_note.md) | Server, embeddings, auto-linking, embedding sweep, near-duplicate threshold |
| 2026-10-13 | [Workspaces, sign-in and sync](../2026-10-13_document-graph-workspaces-signin-and-sync_note.md) | Workspaces, shared sign-in, the Document Index sync job |
| 2026-10-14 | [Passage search](../2026-10-14_document-graph-passage-search_note.md) | Section-by-section search with matching passages |

## Cloud, data and local infrastructure

| Date | Note | Covers |
|------|------|--------|
| 2026-10-11 | [Cloud Run deployment and OAuth](../2026-10-11_cloud-run-deployment-and-oauth_note.md) | Region, first deployment, Google-backed MCP sign-in, consent fix |
| 2026-10-12 | [Release pipeline and access](../2026-10-12_release-pipeline-and-access_note.md) | Cloud Build gates, image retention, deployer impersonation, free-tier builds |
| 2026-10-12 | [Local Compose projects](../2026-10-12_local-compose-projects_note.md) | Three independent Docker projects, localhost ports |
| 2026-10-13 | [Psycopg 3 and round trips](../2026-10-13_psycopg3-and-database-round-trips_note.md) | One driver, token cache, login defaults, single-trip queries |
