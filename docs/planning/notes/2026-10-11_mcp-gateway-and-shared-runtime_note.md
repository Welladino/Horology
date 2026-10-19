# MCP gateway and shared runtime: first build

## Topic
- mcp-gateway-and-shared-runtime

## Context

The [Agent Register MCP tab](https://docs.google.com/spreadsheets/d/1BBZNwuGodU6JlrCk-09L7aZ2BqOBED6Vir0vpDMiJoo/edit#gid=687144154) proposed 23 access rows across Firecrawl/Alexandria, Drive, Supabase, Tavily, GitHub and future DataForSEO. Personal plugin approval settings are not a reliable boundary for which tools and resources an agent may use, so subscription agents needed a server that enforces it.

## Decisions

**One gateway, many adapters (2026-10-11).** A Dockerfile is needed per deployed service, not per provider, so one gateway image holds every provider adapter and enforces one policy, one resource allowlist and shared budgets. Separate provider containers would duplicate policy without restricting upstream authority. Each tool authorises both the tool and the resource; there is no generic HTTP, SQL or provider executor, and provider keys never reach the agent. It started in `subscription-agents/mcp-gateway/` and moved to `mcp-servers/mcp-gateway/` the same day, because it is shared infrastructure.

**Initial scope, approved by the founder.** GitHub limited to `Welladino/Horology` and `Welladino/Article_aggregator_agent`. Supabase project `pyywbjossvjngoxocdxk`: public-schema metadata and sanitised counters only, no auth schema, rows, query text or writes, through a dedicated `horology_agents` login (never `postgres` or the service-role key). Firecrawl and Tavily each 50 credits a day and 500 a month (UTC day, calendar month), with two paid calls per assignment. Credits are reserved before the upstream call, kept on errors, never retried automatically. Access came from operator-provisioned, expiring assignments bound to hashed bearer credentials, so no caller-supplied session ID could reset quotas. The first build had 13 tools; 39 tests passed and a real HTTP MCP handshake, authentication and scope checks passed. Free Alexandria discovery confirmed the Shopify and trends contracts at 5 credits each.

**Code layout (2026-10-11).** The single provider module was split into `integrations/<provider>/` packages (`client.py` for provider calls, `tools.py` for MCP registration), with bounded HTTP and text masking under `shared/`; authentication, authorisation and quotas stayed central.

**Hermes monitoring through the gateway (2026-10-11).** Repository health, recent commits, branch CI and Dependabot reads moved into the gateway (17 tools). Dependabot pages return five alerts to respect the bounded transport, and the persona treats them as a sample. Second-Soul and Code Sentinel got their own 24-hour, GitHub-only assignments; the old `github-monitor` server and Compose service were removed ([archived note](../../archive/notes/2026-08-06_github-monitor-mcp-server_note.md)). Both profiles saw ten gateway tools and were denied other repositories and non-GitHub tools.

**Durable quota ledger in Neon (2026-10-11).** The SQLite ledger on a Docker volume couldn't serialise across cloud instances, so migration `20261011_001` added the `gateway_quotas` schema (reservations, cache, a coordinator row) and the `horology_gateway` login with narrow grants. Each reservation takes a row lock before reading totals. The 14 existing reservations and two cache entries were imported, the gateway login was confirmed unable to read public tables, and the volume was deleted. 52 tests passed.

**Shared runtime, logging and errors (2026-10-11).** Timeouts, logging and error handling were first copied per service, then moved to a package under `mcp-servers/runtime`, and finally to the root `shared-runtime/` package `horology_runtime`, split into logging, error classification, settings and operation wrappers. HTTP and Postgres classifiers are optional, so a future Hermes extension can import it without MCP or database libraries (checked with `python -S`). Every tool call emits an argument-free JSON event with tool, integration, duration, outcome and correlation ID; callers get only an error category and request ID; exception chains are suppressed. Neon got 5-second connect, 10-second statement and 3-second lock timeouts. Docker builds moved to the repository root with one `.dockerignore` that lets in only runtime and service source, requirements and the public CA, so local secrets, policies and clients never enter an image.

**Document graph modules (2026-10-11).** The document graph's client was split into Neon persistence and OpenRouter embeddings, given its own private `.env`, and standardised on `DATABASE_URL_POOLED`.

## Rationale

Centralising authorisation and budgets in one place is what makes them enforceable; shared runtime code keeps the two services' timeouts, logging and error rules identical.

## Impact

- Security checklist before cloud deployment, all since carried out in the [Cloud Run deployment](2026-10-11_cloud-run-deployment-and-oauth_note.md): extended private-address tests, Secret Manager for provider keys, a durable ledger, deliberate ingress and IAM, external tests of the deployed URL, and checks that logs omit tokens and DSNs.
- Later changes replaced assignments with one shared policy ([note](2026-10-13_gateway-shared-policy-and-budgets_note.md)) and removed GitHub and Google adapters ([note](2026-10-12_gateway-provider-scope_note.md)).
- Current design: [gateway](../../architecture/mcp/gateway.md), [MCP services](../../architecture/mcp/mcp-services.md).

## Follow-Ups

- Exhaustive IPv6, DNS-rebinding and remote Firecrawl redirect investigation was deferred; local DNS checks can't control how a provider resolves or redirects.
