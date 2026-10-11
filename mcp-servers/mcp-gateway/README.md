# Restricted subscription-agent MCP gateway

Local prototype based on [Agent Register → MCP](https://docs.google.com/spreadsheets/d/1BBZNwuGodU6JlrCk-09L7aZ2BqOBED6Vir0vpDMiJoo/edit#gid=687144154). One container serves narrow provider adapters at `http://127.0.0.1:8767/mcp`. It does not alter the existing Hermes MCP servers or configure schedules.

## Implemented tools

| Register access | Tools | Local boundary |
| --- | --- | --- |
| 8–9 Drive reads | `drive_list_documents`, `drive_read_document` | Explicit file IDs and exact Sheet ranges; native Google Docs text only |
| 14–15 Supabase metadata | `supabase_list_schema`, `supabase_describe_table` | Fixed parameterized catalog SQL; public columns, key/index structure; no data, defaults or function/view bodies |
| Additional performance access | `supabase_performance_summary` | Database counters and public-table statistics; excludes auth tables and query text |
| 16–17 Tavily search | `tavily_search` | Five results, fixed basic/advanced depth, no automatic upgrades; advanced denied unless assigned |
| 7 Firecrawl basic scrape | `firecrawl_scrape_page` | Exact operator-approved HTTPS URLs; public DNS check; no crawl/actions/PDF parsing/premium options |
| 19–20 GitHub reads | `github_read_file`, `github_read_tree`, `github_search_code`, `github_read_pr_files`, `github_read_records` | Horology and Article_aggregator_agent; explicit file ref; bounded issue/PR/commit/CI summaries |
| Policy inspection | `gateway_status` | Assignment permissions, no credentials |

Provider credentials are required for real calls and are **not copied from installed plugins**. Tests use mocks and real local MCP transport, without paid calls. Adapters have not yet been verified against live provider accounts.

## Local startup

From the Horology root:

```sh
.venv/bin/python mcp-servers/mcp-gateway/scripts/init_local.py
cd mcp-servers/mcp-gateway
docker compose build
docker compose up -d
```

The initializer creates three ignored, private files. It refuses to overwrite existing files so rerunning it does not silently reset session quotas:

- `config/policy.local.json`: operator policy, one assignment with a 24-hour expiry.
- `.env.local`: hashed gateway credential and initially blank provider credentials.
- `config/client.local.json`: localhost URL and raw bearer credential for the local MCP client. Keep this private.

Provider setup, performed by the operator in `.env.local`:

| Variable | Credential restriction |
| --- | --- |
| `GITHUB_TOKEN` | Fine-grained read token for exactly the two repositories; no Actions write or repo administration |
| `GOOGLE_READ_ACCESS_TOKEN` | Short-lived Google OAuth access token with Drive/Docs/Sheets read scopes; automatic refresh is not implemented |
| `SUPABASE_METADATA_DSN` | TLS connection for project `pyywbjossvjngoxocdxk`, dedicated `horology_agents` role, no table SELECT/DML, no ownership or elevated memberships; verify-full needs a trusted certificate chain |
| `TAVILY_API_KEY` | Gateway-only key; provider dashboard limit as additional protection |
| `FIRECRAWL_API_KEY` | Gateway-only key; approved exact URLs must also be populated in both global and assignment policy |

The official public Supabase CA is tracked at `certs/supabase-prod-ca-2021.crt`. The Dockerfile packages it at `/certs/supabase-ca.crt` and sets `PGSSLROOTCERT` to that path, so local Compose and future cloud deployments use the same image without a host certificate mount. Only this public certificate is allowed into the build context; private configuration remains excluded. The adapter retains `sslmode=verify-full` for certificate-chain and hostname verification. This file is a public CA certificate, not a private key or database credential. Its provenance and fingerprint are recorded in the [CA relocation note](../../docs/planning/notes/2026-10-11_gateway-ca-in-repository_note.md). Native clients need `PGSSLROOTCERT` pointing to the repository certificate’s absolute host path.

Never use the Supabase service-role key or a `postgres` login. Catalog queries intentionally work without granting SELECT on application tables. Role provisioning is an operator prerequisite; no SQL migrations or account permissions are changed by this package. Database-wide performance counters aggregate activity across the DB, while table details are restricted to public.

The example exposes only the Agent Register MCP range. Add specific guide/template IDs and bounded register ranges after verifying them. Do not replace the allowlist with unrestricted folder or account access. `auth` is always prohibited. No tool accepts SQL, an API endpoint, arbitrary provider capability, or credentials.

Connect a local MCP client using the URL and Authorization header in `config/client.local.json`. This static-bearer prototype is for localhost clients; it is not a ready-to-connect ChatGPT cloud OAuth service.

## Budget semantics

Firecrawl and Tavily each have separate **50-credit UTC daily / 500-credit calendar-month** caps. Each assignment may make **two paid upstream requests per provider**, shared across that provider's tools. Each individual tool also has a two-invocation limit. Basic Tavily search reserves 1 credit; advanced reserves 2. Basic single-page scrape reserves 1. Failed/ambiguous upstream calls keep their reservation, and there are no automatic retries. Cached successful responses expire after one hour; cache hits count as tool invocations but cost no new credits.

Assignments and expiries are server-provisioned and bound to hashed credentials; clients cannot submit a new session ID to reset counters. Persist the `gateway-state` volume. Multiple connections use atomic SQLite transactions. This ledger is **single-deployment only**, not distributed Cloud Run accounting. Deleting/resetting the state volume loses spending history. Other installed plugins or direct provider usage are outside this ledger.

Firecrawl URLs are exact operator approvals, not arbitrary URLs selected by the agent. Local DNS checks cannot prove how a remote provider will resolve or follow redirects. Verify public target and redirect behavior before approving a URL; keep the list empty otherwise. Results are untrusted source content. Common-token redaction is best effort; arbitrary secrets in repository files are not guaranteed to be detected. CI logs are intentionally unavailable.

## Register coverage still requiring implementation

| Access IDs | Status / remaining work |
| --- | --- |
| 1–3, 6 | Alexandria catalogue contracts were inspected using free discovery. Shopify search/lookup and Trends interest-over-time each advertise 5 credits. No paid execution adapter yet: verify the direct API contract, assigned market/store scope and live response envelope first. |
| 4–5 | Alibaba capability unverified; disabled. |
| 10–11 | Drive creation/template copy and own-draft editing not implemented. Need output-folder IDs, assignment ownership and acceptance/freeze lifecycle, revision checks, and crash-safe idempotency. |
| 12–13 | Sheets writes/claiming not implemented. Need exact allowed columns and transitions, single-writer or atomic coordinator, numeric ID allocation, lease expiry and replay handling. |
| 18 | Tavily extraction optional; disabled until the primary page reader is chosen and billing validated. |
| 19–20 | Files, immediate trees, scoped search and truncated PR patches implemented. Full recursive trees, pagination and CI logs remain unavailable. |
| 21 | GitHub planning-note writer optional and disabled; Stage 3 skill and branch/path rules pending. |
| 22–23 | DataForSEO future scope; disabled. |

No unavailable operation is silently forwarded to a broader plugin. The package fails closed for missing credentials, unassigned tools, resources, expired assignments and exhausted budgets. Gateway restrictions do not prevent an agent using another broad plugin; scheduled-client tool isolation remains a separate prerequisite.

## Verification

```sh
# Offline unit tests
../../.venv/bin/python -m pytest tests/ -v
# Starts a temporary native server on localhost; no provider credentials
../../.venv/bin/python tests/smoke.py
# Test the running gateway container, using generated local credentials
../../.venv/bin/python tests/smoke.py --existing
# Stop only this standalone stack; preserve spending history
docker compose down
```

For later GCP deployment: implement OAuth compatible with the intended clients, Secret Manager, distributed atomic quotas/assignment registry, deny-by-default tool isolation, audit/monitoring and provider credential refresh. Terraform can provision infrastructure after these release gates are resolved. Nothing here deploys GCP or verifies cloud scheduled-agent support.

## Code layout

`server.py` assembles the authenticated MCP server. Each integration registers its tools through `tools.py`; `shared/access.py` applies the same assignment authorization and quotas through `policy.py`. Fixed provider operations and provider-specific scope checks live in each integration’s `client.py`. Package `__init__.py` files contain only package descriptions. `shared/http.py` bounds transport responses and disables redirects and environment proxies; `shared/text.py` sanitizes bounded output. All integrations ship in one Docker image and use one MCP endpoint. Google OAuth remains deferred.

Local policy examples and private client/policy files live under `config/`; the initializer lives under `scripts/`; unit checks and the MCP smoke client live under `tests/`. Docker files and `.env.local` remain at the gateway root.

## GitHub monitoring and Hermes

The gateway includes `github_repo_status`, `github_recent_commits`, `github_ci_status`, and `github_dependabot_alerts` in addition to existing GitHub reads. Dependabot returns up to five alerts; PR patches remain partial. `compose.hermes-network.yaml` optionally joins the existing `horology_default` network with alias `horology-mcp-gateway`. Start the main stack first, then use both Compose files to recreate the gateway. Second-Soul and Code Sentinel use separate GitHub-only assignments covering policy-approved repositories; its local credential expires after 24 hours and tool limits do not reset on restart. Per-run renewal/provisioning for schedules remains future work.

Application tool logs emit JSON to stdout with assignment, tool, integration, duration, outcome and request ID. Error responses expose only a category and request ID. No arguments, results, secrets or raw exceptions are logged by this layer. HTTP retains its 25-second timeout; Supabase retains its five-second connection and three-second statement timeout. No automatic retries or quota refunds on upstream failures. Use `docker compose logs gateway` with the same Compose files used to start it.

Timeout settings and logging/error handling are imported from the common package at `../../shared-runtime/horology_runtime/`. Change `settings.py` or `operations.py` there and rebuild both images. Native development requires installing the shared runtime as described in its README. Docker build context is the repository root, using its secret-safe `.dockerignore`; use the documented Compose commands.
