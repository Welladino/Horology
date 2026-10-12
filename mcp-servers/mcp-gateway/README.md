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

Provider credentials are required for real calls and are **not copied from installed plugins**. Tests use mocks and real local MCP transport, without paid calls. GitHub, Supabase, Tavily and Firecrawl have passed bounded live checks; Google Drive provider OAuth remains deferred.

## Local startup

From the Horology root:

```sh
.venv/bin/python mcp-servers/mcp-gateway/scripts/init_local.py
cd mcp-servers/mcp-gateway
# Apply the quota migration and configure GATEWAY_DATABASE_URL first (see below).
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
| `GATEWAY_DATABASE_URL` | Neon pooled connection using `horology_gateway`; access only to `gateway_quotas` tables |
| `GITHUB_TOKEN` | Fine-grained read token for exactly the two repositories; no Actions write or repo administration |
| `GOOGLE_READ_ACCESS_TOKEN` | Short-lived Google OAuth access token with Drive/Docs/Sheets read scopes; automatic refresh is not implemented |
| `SUPABASE_METADATA_DSN` | TLS connection for project `pyywbjossvjngoxocdxk`, dedicated `horology_agents` role, no table SELECT/DML, no ownership or elevated memberships; verify-full needs a trusted certificate chain |
| `TAVILY_API_KEY` | Gateway-only key; provider dashboard limit as additional protection |
| `FIRECRAWL_API_KEY` | Gateway-only key; approved exact URLs must also be populated in both global and assignment policy |

The official public Supabase CA is tracked at `certs/supabase-prod-ca-2021.crt`. The Dockerfile packages it at `/certs/supabase-ca.crt` and sets `PGSSLROOTCERT` to that path, so local Compose and future cloud deployments use the same image without a host certificate mount. Only this public certificate is allowed into the build context; private configuration remains excluded. The adapter retains `sslmode=verify-full` for certificate-chain and hostname verification. This file is a public CA certificate, not a private key or database credential. Its provenance and fingerprint are recorded in the [CA relocation note](../../docs/planning/notes/2026-10-11_gateway-ca-in-repository_note.md). Native clients need `PGSSLROOTCERT` pointing to the repository certificate’s absolute host path.

Never use the Supabase service-role key or a `postgres` login. Catalog queries intentionally work without granting SELECT on application tables. Role provisioning is an operator prerequisite; no SQL migrations or account permissions are changed by this package. Database-wide performance counters aggregate activity across the DB, while table details are restricted to public.

The example exposes only the Agent Register MCP range. Add specific guide/template IDs and bounded register ranges after verifying them. Do not replace the allowlist with unrestricted folder or account access. `auth` is always prohibited. No tool accepts SQL, an API endpoint, arbitrary provider capability, or credentials.

Connect a local MCP client using the URL and Authorization header in `config/client.local.json`. Local clients use assignment tokens. Cloud client OAuth is described below; native browser verification and external ingress approval remain pending.

## Budget semantics

Firecrawl and Tavily each have separate **50-credit UTC daily / 500-credit calendar-month** caps. Each assignment may make **two paid upstream requests per provider**, shared across that provider's tools. Each individual tool also has a two-invocation limit. Basic Tavily search reserves 1 credit; advanced reserves 2. Basic single-page scrape reserves 1. Failed/ambiguous upstream calls keep their reservation, and there are no automatic retries. Cached successful responses expire after one hour; cache hits count as tool invocations but cost no new credits.

Assignments and expiries are server-provisioned and bound to hashed credentials; clients cannot submit a new session ID to reset counters. Quotas and assignment-scoped response caches live in Neon under `gateway_quotas`. Each reservation locks a single coordinator row for its transaction before checking totals and inserting usage, so concurrent instances share the same caps. Database failures prevent upstream calls; there is no local fallback or automatic refund. Table creation belongs to Alembic, not server startup. Other installed plugins or direct provider usage are outside this ledger.

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
# Provider tests use mocks; quota integration tests require disposable Postgres.
# Set GATEWAY_TEST_DATABASE_URL (admin) and GATEWAY_TEST_RUNTIME_URL (restricted role).
../../.venv/bin/python -m pytest tests/ -v
# Starts a temporary native server; requires GATEWAY_DATABASE_URL, no provider calls.
../../.venv/bin/python tests/smoke.py
# Test the running gateway container, using generated local credentials
../../.venv/bin/python tests/smoke.py --existing
# Stop only this standalone stack; preserve spending history
docker compose down
```

Cloud Run deployment and Google-backed gateway OAuth are implemented with gcloud and Secret Manager. Scheduled assignment provisioning, native client verification, Google Drive credential refresh and remaining deployment monitoring are pending; see the deployment planning note. Scheduled subscription-agent support is not yet verified.

## Code layout

`server.py` assembles the authenticated MCP server. Each integration registers its tools through `tools.py`; `shared/access.py` applies the same assignment authorization and quotas through `policy.py`. Fixed provider operations and provider-specific scope checks live in each integration’s `client.py`. Package `__init__.py` files contain only package descriptions. `shared/http.py` bounds transport responses and disables redirects and environment proxies; `shared/text.py` sanitizes bounded output. All integrations ship in one Docker image and use one MCP endpoint. Google Drive provider OAuth remains deferred.

Local policy examples and private client/policy files live under `config/`; the initializer lives under `scripts/`; unit checks and the MCP smoke client live under `tests/`. Docker files and `.env.local` remain at the gateway root.

## GitHub monitoring and Hermes

The gateway includes `github_repo_status`, `github_recent_commits`, `github_ci_status`, and `github_dependabot_alerts` in addition to existing GitHub reads. Dependabot returns up to five alerts; PR patches remain partial. `compose.hermes-network.yaml` optionally joins the existing `horology_default` network with alias `horology-mcp-gateway`. Start the main stack first, then use both Compose files to recreate the gateway. Second-Soul and Code Sentinel use separate GitHub-only assignments covering policy-approved repositories; its local credential expires after 24 hours and tool limits do not reset on restart. Per-run renewal/provisioning for schedules remains future work.

Application tool logs emit JSON to stdout with assignment, tool, integration, duration, outcome and request ID. Error responses expose only a category and request ID. No arguments, results, secrets or raw exceptions are logged by this layer. HTTP retains its 25-second timeout; Supabase retains its five-second connection and three-second statement timeout. No automatic retries or quota refunds on upstream failures. Use `docker compose logs gateway` with the same Compose files used to start it.

Timeout settings and logging/error handling are imported from the common package at `../../shared-runtime/horology_runtime/`. Change `settings.py` or `operations.py` there and rebuild both images. Native development requires installing the shared runtime as described in its README. Docker build context is the repository root, using its secret-safe `.dockerignore`; use the documented Compose commands.

## Neon quota schema setup

Use root Alembic with the direct owner `DATABASE_URL`, never the pooled runtime login. Migration `20261011_001` requires `GATEWAY_DB_PASSWORD`; it creates the dedicated `horology_gateway` role and `gateway_quotas` schema. Save the password privately before migration, and configure `.env.local` with `GATEWAY_DATABASE_URL`, using the Neon pooled host and that role/password. The migration password stays in the root private environment; it is not a runtime input. See [Alembic workflow](../../docs/runbook/db/alembic_workflow.md).

```sh
# From the repository root, after setting GATEWAY_DB_PASSWORD privately:
.venv/bin/alembic upgrade head
```

The runtime role can read and insert reservations, update/read the coordinator lock and read/insert/update cache entries. It cannot delete/reset quota history or create quota tables. Alembic downgrade destroys quota accounting and should not be used on an active gateway. Native smoke runs need the same private `GATEWAY_DATABASE_URL`; the smoke script does not load `.env.local` itself. No persistent local state volume is used.

Neon TLS uses the public CA bundle from certifi and `verify-full` for Neon hosts, overriding the container Supabase-specific PGSSLROOTCERT for this connection only. Supabase continues to use its packaged official CA.

## Cloud OAuth

Cloud Run can use Google-backed MCP OAuth. The Google client is a Web application with redirect URI `https://mcp-gateway-366292507424.us-central1.run.app/auth/google/callback`.

Private gateway inputs:

```dotenv
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
GATEWAY_OAUTH_ENABLED=true
GATEWAY_OAUTH_ASSIGNMENTS={"approved-email@example.com":"existing-policy-assignment"}
GATEWAY_PUBLIC_URL=https://mcp-gateway-366292507424.us-central1.run.app
```

`GATEWAY_OAUTH_ASSIGNMENTS` must refer to operator-approved policy assignments. These variables do not belong in Git. In Cloud Run, Google credentials use pinned Secret Manager versions. The schema is installed through Alembic, not server startup. Local Compose stays on its existing assignment-token configuration unless OAuth is explicitly enabled and a local callback is registered with Google.

The OAuth modules live in `shared/oauth/`; token/state expiry policy lives in `shared-runtime/horology_runtime/settings.py`. OAuth refresh preserves assignment expiry, tool limits and quota history. Google sign-in does not provide Google Drive access.

Connect Codex with `codex mcp add horology --url https://mcp-gateway-366292507424.us-central1.run.app/mcp --oauth-client-registration dcr`, then complete the browser sign-in and gateway consent. If login needs restarting, use `codex mcp login horology --oauth-client-registration dcr`. Google credentials belong only to the gateway; do not provide them as the Codex client's credentials.

See [OAuth implementation note](../../docs/planning/notes/2026-10-11_gateway-oauth_note.md) and [deployment runbook](../../docs/runbook/gcp/mcp_deployment.md). Browser verification status is recorded in the deployment runbook.

## Release builds and consent page

Release source is submitted to the root `cloudbuild.yaml` pipeline; see [Cloud Build runbook](../../docs/runbook/gcp/cloud_build.md). Keep the local Compose image at `latest`; Cloud Build publishes unique build IDs and a convenience `latest` tag. Deploy immutable digests.

Google consent presentation lives in `shared/oauth/consent_page.py` and `shared/oauth/consent.css`. The provider passes verified account identity and approved assignment permissions to the renderer. The stylesheet is protected by a CSP hash, and the SDK-validated callback origin remains allowed for consent redirects. Updating the page requires rebuilding and redeploying the gateway.

### Local Docker names

The standalone Compose project and container are `horology-mcp-gateway`; its local image is `horology-mcp-gateway:latest`. The root `horology-hermes` project contains only `horology-hermes`; document-graph has its own `horology-document-graph-mcp` project. Cloud Run/Artifact Registry names remain `mcp-gateway`. The optional Hermes network alias stays `horology-mcp-gateway`.
