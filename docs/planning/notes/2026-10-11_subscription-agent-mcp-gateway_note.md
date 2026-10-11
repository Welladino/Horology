# Implementation Note

## Topic

2026-10-11 — Local restricted MCP gateway for subscription agents.

## Context

The [Agent Register MCP tab](https://docs.google.com/spreadsheets/d/1BBZNwuGodU6JlrCk-09L7aZ2BqOBED6Vir0vpDMiJoo/edit#gid=687144154) proposes 23 access rows across Firecrawl/Alexandria, Drive, Supabase, Tavily, GitHub and future DataForSEO. Personal plugin approval settings are not a reliable resource/tool authorization boundary. Subscription schedules and Stage 3 skills are not yet implemented.

## Decision

Add `subscription-agents/mcp-gateway/` as a standalone local prototype. **One Dockerfile builds one gateway service containing multiple provider adapters.** A Dockerfile is needed per independently deployed service, not per provider or tool. Preserve the existing document-graph and GitHub-monitor servers for Hermes; they remain separate services.

Use operator-provisioned, expiring assignments bound to hashed bearer credentials. No caller-supplied session ID can reset quotas. Fixed tools authorize both tool and resource scope; there is no generic HTTP, SQL or provider executor. Provider credentials remain in server environment and are never sent to the agent.

Approved scope from the founder in this session:

- GitHub: `Welladino/Horology` and `Welladino/Article_aggregator_agent` only.
- Supabase: project `pyywbjossvjngoxocdxk`; public schema metadata and sanitized database/public-table performance counters. No auth schema, application row reads, query text, logs or writes.
- Separate Firecrawl and Tavily budgets: **50 credits daily, 500 monthly, two paid requests per assignment/session per provider**. Each tool has two invocations per assignment. UTC day/calendar month accounting.

SQLite persists reservations and one-hour response caches on a Docker named volume. Reserve before upstream requests, retain reservations on errors, and do not retry automatically. This is a single local deployment; distributed cloud execution requires a different atomic store.

## Rationale

One gateway centralizes authorization, resource allowlists and shared budgets. Individual provider containers would duplicate policy and do not themselves restrict upstream authority. Separate adapters keep future service separation possible when scaling or isolation needs justify it.

Local static bearer authentication is sufficient to verify transport and scope controls on loopback. Cloud OAuth, private publication and scheduled-client support need separate verification before deployment. Broad personal plugins can remain installed, but automated client sessions must be configured so they cannot bypass the gateway through those plugins.

## Impact

Thirteen tools cover policy status, bounded GitHub files/tree/search/PR patches/record summaries, explicit-ID Drive/Docs/Sheets reads, Supabase schema/table metadata and performance, Tavily search and optional exact-URL Firecrawl basic scrape. Supabase uses catalog queries with a dedicated metadata role and read-only transactions; defaults, executable definitions and foreign-target identities are omitted.

The initial allowlist contains only the Agent Register MCP range. Google OAuth refresh and provider credentials are not provisioned. Firecrawl URL approvals remain empty. Advanced Tavily search is unassigned by default.

**This is an initial local implementation, not completion of all 23 register rows.** The README maps every remaining row: Alexandria execution; Alibaba; Drive deliverable creation/own-draft editing; coordinated register writes/claiming; optional Tavily extraction; optional GitHub note writes; future DataForSEO. Missing contracts/scopes fail closed rather than forwarding to broad plugins. The Sheet itself is unchanged.

Free Alexandria discovery verified Shopify `catalog/search_catalog` and `catalog/lookup_catalog`, and `firecrawl-trends/trends/interest_over_time`, each advertising 5 credits per request. No paid provider was executed. Direct API integration and response envelopes still need verification; do not infer that a plugin credential can be reused by a Docker server.

Verification: **39 tests passed (23 existing + 16 gateway), 14 unrelated main-stack Docker tests skipped**. The final 13-tool container passed real HTTP MCP initialization/authentication/scope checks. `pip-audit` reported no known vulnerabilities in the gateway requirements. Gateway unit tests cover assignment expiry, resource denial, parameterized metadata SQL, two-call/shared daily/monthly budgeting, concurrent reservations, persistent counters, assignment cache isolation, search qualifier injection and private-URL denial. Real native and Docker MCP tests cover initialization, tool discovery, authenticated status, missing/invalid authentication and scope rejection. Provider adapters are mocked; live provider behavior remains unverified. Existing Horology tests were run; the unrelated main-stack Docker suite skipped because its Docker socket was inaccessible in the sandbox.

## Follow-Ups

1. Verify/register Google guide, template and output-folder IDs plus exact workflow fields/transitions; implement crash-safe draft ownership/idempotency, founder acceptance freeze, numeric ID allocation and work leases before enabling writes.
2. Provision dedicated provider credentials and the Supabase metadata role outside the agent session; test narrow live reads. Never reuse admin/service-role credentials.
3. Verify direct Alexandria execution contracts, assigned store/market and response envelopes. Keep Alibaba unavailable until verified.
4. Review Firecrawl target/redirect behavior before approving exact URLs. Local DNS checks do not control remote-provider DNS or redirects.
5. Select the primary page reader; keep optional extract and DataForSEO disabled until endpoint costs and scopes are approved.
6. Add Stage 3 note-writing skill and separately scoped branch/path writer only if wanted.
7. Before Terraform/GCP: implement OAuth/client compatibility, credential refresh, Secret Manager, distributed budgets, assignment scheduling/isolation, audit logs and monitoring. No cloud resources were deployed.

Sources checked: [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Tavily credits](https://docs.tavily.com/documentation/api-credits), [Firecrawl scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape), [GitHub contents](https://docs.github.com/en/rest/repos/contents), [Supabase MCP safety guidance](https://supabase.com/docs/guides/ai-tools/mcp). Alexandria prices/contracts came from three bounded free discovery calls in the connected Firecrawl plugin, not paid provider execution.
