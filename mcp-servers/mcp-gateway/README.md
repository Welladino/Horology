# Restricted subscription-agent MCP gateway

Local prototype based on [Agent Register → MCP](https://docs.google.com/spreadsheets/d/1BBZNwuGodU6JlrCk-09L7aZ2BqOBED6Vir0vpDMiJoo/edit#gid=687144154). One container serves narrow provider adapters at `http://127.0.0.1:8767/mcp`. It does not alter the existing Hermes MCP servers or configure schedules.

## Implemented tools

| Register access | Tools | Local boundary |
| --- | --- | --- |
| 14–15 Supabase metadata | `supabase_list_schema`, `supabase_describe_table` | Fixed parameterized catalog SQL; public columns, key/index structure; no data, defaults or function/view bodies |
| Additional performance access | `supabase_performance_summary` | Database counters and public-table statistics; excludes auth tables and query text |
| 16–17 Tavily search | `tavily_search` | Five results, fixed basic/advanced depth, no automatic upgrades; advanced denied unless approved in JSON policy |
| 1–6 Alexandria reads | `firecrawl_discover_tools`, `firecrawl_shopify_search`, `firecrawl_shopify_product`, `firecrawl_alibaba_search`, `firecrawl_alibaba_product`, `firecrawl_trends` | Fixed read-only contracts; approved country scope; detail IDs/URLs from the same authenticated client’s search within one hour; 5 credits per execution, free metadata discovery |
| 18 Tavily extraction | `tavily_extract_pages` | 1–5 exact approved URLs, basic depth, bounded content, 1-credit reservation; no automatic upgrade |
| 7 Firecrawl basic scrape | `firecrawl_scrape_page` | Any public HTTPS URL; shared public-address check; no crawl/actions/PDF parsing/premium options |
| Policy inspection | `gateway_status` | Shared policy permissions, no credentials |

Provider credentials are required for real calls and are **not copied from installed plugins**. Tests use mocks and real local MCP transport, without paid calls. Supabase, Tavily and Firecrawl have passed bounded live checks. GitHub and Google adapters are parked.

## Local startup

From the Horology root:

```sh
.venv/bin/python mcp-servers/mcp-gateway/scripts/setup_local_gateway.py
cd mcp-servers/mcp-gateway
# Apply the quota migration and configure GATEWAY_DATABASE_URL first (see below).
docker compose build
docker compose up -d
```

The initializer creates three ignored, private files. It refuses to overwrite existing files so rerunning it does not overwrite credentials or configuration:

- `config/policy.local.json`: one shared JSON tool/resource policy with no assignment or access-expiry field.
- `.env.local`: hashed gateway credential and initially blank provider credentials.
- `tests/mcp_servers/gateway/fixtures/private/client.local.json`: localhost URL and raw bearer credential for the local MCP client. Keep this private.

Provider setup, performed by the operator in `.env.local`:

| Variable | Credential restriction |
| --- | --- |
| `GATEWAY_DATABASE_URL` | Neon pooled connection using `horology_gateway`; access only to `gateway_quotas` tables |
| `SUPABASE_METADATA_DSN` | TLS connection for project `pyywbjossvjngoxocdxk`, dedicated `horology_agents` role, no table SELECT/DML, no ownership or elevated memberships; verify-full needs a trusted certificate chain |
| `TAVILY_API_KEY` | Gateway-only key; provider dashboard limit as additional protection |
| `FIRECRAWL_API_KEY` | Gateway-only key; JSON firecrawl.url_policy must be public_https; tool permission and budgets still apply |

The official public Supabase CA is tracked at `certs/supabase-prod-ca-2021.crt`. The Dockerfile packages it at `/certs/supabase-ca.crt` and sets `PGSSLROOTCERT` to that path, so local Compose and future cloud deployments use the same image without a host certificate mount. Only this public certificate is allowed into the build context; private configuration remains excluded. The adapter retains `sslmode=verify-full` for certificate-chain and hostname verification. This file is a public CA certificate, not a private key or database credential. Its provenance and fingerprint are recorded in the [CA relocation note](../../docs/planning/notes/2026-10-11_gateway-ca-in-repository_note.md). Native clients need `PGSSLROOTCERT` pointing to the repository certificate’s absolute host path.

Never use the Supabase service-role key or a `postgres` login. Catalog queries intentionally work without granting SELECT on application tables. Role provisioning is an operator prerequisite; no SQL migrations or account permissions are changed by this package. Database-wide performance counters aggregate activity across the DB, while table details are restricted to public.

The example exposes only the Agent Register MCP range. Add specific guide/template IDs and bounded register ranges after verifying them. Do not replace the allowlist with unrestricted folder or account access. `auth` is always prohibited. No tool accepts SQL, an API endpoint, arbitrary provider capability, or credentials.

Connect a local MCP client using the URL and Authorization header in `tests/mcp_servers/gateway/fixtures/private/client.local.json`. Local clients use configured bearer credentials. Cloud client OAuth is described below; native browser verification and external ingress approval remain pending.

## Budget semantics

Firecrawl and Tavily each have separate **50-credit UTC daily / 500-credit calendar-month** caps, shared across all authenticated clients and tools for that provider. There are no per-session, per-assignment or per-tool call/credit quotas. Basic Tavily search/extraction and single-page scraping reserve 1 credit; advanced Tavily reserves 2; fixed Shopify/Alibaba/trends calls reserve 5. Free discovery and cache hits spend no new credits. Unknown or changed Alexandria prices fail closed. Failed/ambiguous calls retain reservations; no automatic retries or refunds. Cached responses expire after one hour. Tool permissions, resource scopes and bounded request/output sizes still apply.

There are no assignments, per-run IDs or policy authorization expiry. Spreadsheet access IDs are not included in runtime policy or status responses; permissions come from named tools and resource scopes in JSON. Authentication comes from OAuth client grants or local bearer credentials; one JSON `access` block defines allowed tools, schemas, Alexandria operations/markets and Tavily extraction URLs. Shared budget checks are atomic and use database time. Usage/cache rows are keyed by client identity for auditing/cache isolation, not quotas or permissions. Daily/monthly totals span all clients. Database failure blocks upstream calls; no local fallback or automatic refunds.

Firecrawl accepts agent-selected public HTTPS URLs under JSON `firecrawl.url_policy=public_https`. Public-address checks are shared through `horology_runtime.urls`; local/private/link-local/metadata addresses and mixed public/private DNS results are rejected. Tavily extraction retains its exact URL approvals. Local DNS checks cannot prove how a remote provider will resolve or follow redirects. Results are untrusted source content. Common-token redaction is best effort and cannot detect every secret pattern.

## Register coverage still requiring implementation

| Access IDs | Status / remaining work |
| --- | --- |
| 1–3, 6 | Fixed global Shopify search/product and trends interest-over-time adapters implemented. Store-specific search, lookup batches, related/rising trends and arbitrary catalogue execution remain unavailable. |
| 4–5 | Published Alibaba retail/search and retail/product contracts verified through free discovery; fixed adapters implemented. First-page search is mostly sponsored; inventory is not established. |
| 18 | Basic bounded extraction implemented; same Tavily shared budget/call ledger as search. Exact URL approval required. |
| 21 | Removed. Planning deliverables will be draft Google Docs in approved domain planning folders. No GitHub writes are exposed. |
| 22–23 | DataForSEO future scope; disabled. |

No unavailable operation is silently forwarded to a broader plugin. The package fails closed for missing credentials, unapproved tools/resources and exhausted budgets. Gateway restrictions do not prevent an agent using another broad plugin; scheduled-client tool isolation remains a separate prerequisite.

## Verification

Run from the repository root:

```sh
.venv/bin/python -m pytest tests/ -v
# The HTTP smoke helper requires a disposable migrated GATEWAY_DATABASE_URL.
.venv/bin/python tests/mcp_servers/gateway/smoke.py
# Verify an existing local gateway using tests/mcp_servers/gateway/fixtures/private/client.local.json.
.venv/bin/python tests/mcp_servers/gateway/smoke.py --existing
```

Provider calls are mocked. Quota/OAuth persistence checks require disposable PostgreSQL and automatically skip without its explicit test DSNs. Native HTTP smoke makes no paid-provider requests. Scheduled-runtime verification remains pending; spending caps reset by UTC day/calendar month; no schedule is configured by these files.

## Code layout

`server.py` assembles the authenticated MCP server. Each integration registers its tools through `tools.py`; `shared/access.py` applies shared JSON authorization through `policy.py` and awaits the quota repository. Fixed provider operations and provider-specific scope checks live in each integration’s `client.py`. Package `__init__.py` files contain only package descriptions. `shared/http.py` bounds transport responses and disables redirects and environment proxies; `shared/text.py` sanitizes bounded output. The three active provider integrations ship in one Docker image and use one MCP endpoint. GitHub/Google adapters are parked outside this runtime.

Runtime policy examples and private local/cloud policy candidates live under `config/`; private manual-test clients live under `tests/mcp_servers/gateway/fixtures/private/`; the initializer lives under `scripts/`; unit checks and the MCP smoke client live under the repository’s `tests/mcp_servers/gateway/`. Docker files and `.env.local` remain at the gateway root.


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
GATEWAY_PUBLIC_URL=https://mcp-gateway-366292507424.us-central1.run.app
```

Who may sign in is managed in Google Auth Platform → Audience: the app is External with publishing status Testing, and only listed test users can complete Google sign-in. Keep it in Testing; publishing it would let any Google account sign in, because the gateway no longer keeps its own email list. Removing a test user blocks new sign-ins only; an already connected client keeps working until its gateway refresh token lapses (7 days without use) or its grant is revoked. These variables do not belong in Git. In Cloud Run, Google credentials use pinned Secret Manager versions. The schema is installed through Alembic, not server startup. Local Compose stays on its existing assignment-token configuration unless OAuth is explicitly enabled and a local callback is registered with Google.

The OAuth modules live in `shared-runtime/horology_runtime/oauth/` (shared with the document graph; the gateway uses scope `gateway` and table `gateway_auth.records`); token/state expiry policy lives in `shared-runtime/horology_runtime/settings.py`. OAuth refresh renews tokens while preserving client grant identity and shared daily/monthly spending history. Token and registration TTLs remain; there is no assignment expiry. Google sign-in does not provide Google Drive access.

Connect Codex with `codex mcp add horology --url https://mcp-gateway-366292507424.us-central1.run.app/mcp --oauth-client-registration dcr`, then complete the browser sign-in and gateway consent. If login needs restarting, use `codex mcp login horology --oauth-client-registration dcr`. Google credentials belong only to the gateway; do not provide them as the Codex client's credentials.

See [OAuth implementation note](../../docs/planning/notes/2026-10-11_gateway-oauth_note.md) and [deployment runbook](../../docs/runbook/gcp/mcp_deployment.md). Browser verification status is recorded in the deployment runbook.

## Release builds and consent page

Release source is submitted to the root `cloudbuild.yaml` pipeline; see [Cloud Build runbook](../../docs/runbook/gcp/cloud_build.md). Keep the local Compose image at `latest`; Cloud Build publishes unique build IDs and a convenience `latest` tag. Deploy immutable digests.

Google consent presentation lives in `shared-runtime/horology_runtime/oauth/consent_page.py` and `consent.css`; the gateway's wording comes from `shared/consent.py`. The provider passes the verified account and the gateway's permission sections to the renderer. The stylesheet is protected by a CSP hash, and the SDK-validated callback origin remains allowed for consent redirects. Updating the page requires rebuilding and redeploying the gateway.

### Local Docker names

The standalone Compose project and container are `horology-mcp-gateway`; its local image is `horology-mcp-gateway:latest`. The root `horology-hermes` project contains only `horology-hermes`; document-graph has its own `horology-document-graph-mcp` project. Cloud Run/Artifact Registry names remain `mcp-gateway`. The optional Hermes network alias stays `horology-mcp-gateway`.

## Parked native-connector alternatives

GitHub and Google Drive/Docs/Sheets adapters were removed on 2026-10-13 in favour of native platform connectors, whose permissions are outside this gateway's policy. The code, tests, authorization helper and unshipped migration remain in Git history (`git show d643223:placeholders/connectors/README.md`).

The active gateway exposes 13 tools: status, Supabase metadata/performance, capped Tavily search/extraction and fixed Firecrawl scrape/Alexandria reads. Google-backed MCP identity OAuth remains active; it grants no Google document access. Retired provider credentials remain only in the ignored, untracked `placeholders/connectors/.env.local` until the operator revokes them; the cloud `GITHUB_TOKEN` binding is removed by the next gateway release.

Tests and the local MCP smoke helper live at `tests/mcp_servers/gateway/` in the repository root. No Cloud Build or deployment was run for this extraction.

## Assignment removal release dependency

Local source/configuration now uses shared `access`, JSON-list `GATEWAY_TOKEN_HASHES` and Audience-managed Google sign-in. Alembic `20261013_001` renames the historical quota/cache identity columns to `client_id`, preserving all rows and budgets. Apply that migration and update cloud configuration during the later release, before directing traffic to the new image. Existing cloud deployment and OAuth sessions have not been changed by local preparation. Live client revocation verification remains deferred to release testing.

## Async gateway database layer (local source)

```text
database/
├── connection.py
└── repositories/
    ├── quotas.py
    ├── cache.py
    └── oauth.py
```

`connection.py` owns a Psycopg 3 `AsyncConnectionPool`, opened and closed on the server's event loop by the HTTP application lifespan. The pool starts empty and grows to at most four connections per gateway process. Connection/acquisition, statement and lock limits come from `horology_runtime.settings`. Transactions commit on success and roll back on exceptions or cancellation. Prepared statements are disabled for transaction-pool compatibility; Neon TLS verification remains enabled.

Repositories own SQL: quotas reserve shared daily/monthly credits under the coordinator row lock; cache reads/writes client-scoped JSON with a one-hour TTL; OAuth stores hashed opaque credentials and preserves advisory-lock transactions for code redemption, refresh rotation and grant revocation. These are SQL connections through the Neon pooled host, not REST CRUD. The separate Supabase metadata adapter, document-graph server and Alembic migrations retain their existing drivers.

`setup_local_gateway.py` generates the local bearer token with `secrets.token_urlsafe(32)`, puts its SHA-256 hash in `.env.local`, and saves the raw token in ignored mode-0600 `tests/mcp_servers/gateway/fixtures/private/client.local.json` for manual tests. `tests/mcp_servers/gateway/fixtures/private/client.cloud.json` is an earlier private cloud-test client configuration; it is not a provider credential or the OAuth connection managed by Codex/ChatGPT. Neither private JSON file is packaged or uploaded.

This refactor is local only. Cloud Build, deployment and production migrations have not run.

## Configuration sources

- `config/policy.example.json` is tracked runtime policy documentation/default setup input, also used by mocked tests. It is not a private credential.
- `config/policy.local.json` is ignored operator configuration mounted by local Docker Compose at `/config/policy.json`. It is runtime configuration, not a test fixture.
- `config/policy.cloud.json` is the tracked cloud policy. It holds no credentials and is copied into the image at `/config/policy.json`, where `GATEWAY_POLICY` points. Changing it needs a rebuild and deploy; there is no policy secret for new revisions.
- `config/policy.cloud.secret-v4.local.json` is an ignored copy of the old Secret Manager policy (`horology-gateway-policy:4`) still served by revision `mcp-gateway-00008-kqw`; `policy.cloud.snapshot.local.json` records its version, revision and digest. Keep both until the new image is released, for rollback reference.
- `tests/mcp_servers/gateway/fixtures/private/client.{local,cloud}.json` contain private manual-test bearer credentials. Git and Cloud Build source exclude this directory; runtime images do not package tests. OAuth clients manage their own tokens independently.

Psycopg 3 handles everything: gateway Neon persistence, the Supabase metadata adapter (read-only session, `verify-full` TLS, no prepared statements for the pooler), document-graph, Alembic (`alembic/env.py` selects the `postgresql+psycopg` driver for any URL form), CI and tests. Psycopg 2 was removed on 2026-10-13.

### Policy drift and releases

Local Compose uses `config/policy.local.json`, mounted over the baked file. Cloud uses the tracked `config/policy.cloud.json` inside the image, so the deployed policy is whatever the deployed image digest was built from. Review policy changes in Git like code. Until the next release, revision `mcp-gateway-00008-kqw` still serves the old policy secret; see the deployment runbook for the release steps.
