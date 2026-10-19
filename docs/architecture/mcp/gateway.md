# Gateway

The gateway (`mcp-servers/mcp-gateway/`) gives agents a few external capabilities through fixed, capped tools. Provider keys stay inside it; agents never see them.

## Tools

| Provider | Tools | Boundary | Credits |
|---|---|---|---|
| — | `gateway_status` | Shows the policy's permissions; no credentials | free |
| Supabase | `supabase_list_schema`, `supabase_describe_table` | Fixed catalog queries on project `pyywbjossvjngoxocdxk`, schema `public`: columns, keys and indexes; no row data, defaults or function bodies | free |
| Supabase | `supabase_performance_summary` | Database counters and public-table statistics; no auth tables or query text | free |
| Tavily | `tavily_search` | Five results. `advanced: true` needs the `tavily_advanced_search` permission and is never applied automatically | 1, or 2 advanced |
| Tavily | `tavily_extract_pages` | 1–5 public HTTPS URLs, basic depth, bounded content | 1 |
| Firecrawl | `firecrawl_scrape_page` | One public HTTPS URL; no crawl, browser actions or PDF parsing | 1 |
| Firecrawl Alexandria | `firecrawl_discover_tools` | Reads the published contracts | free |
| Firecrawl Alexandria | `firecrawl_shopify_search`, `firecrawl_shopify_product`, `firecrawl_alibaba_search`, `firecrawl_alibaba_product`, `firecrawl_trends` | Fixed read-only contracts; one ISO country code per call (`WORLDWIDE` for trends only); product IDs must come from the same client's search within an hour | 5 |

`gateway_status` lists 14 names: these 13 tools plus the `tavily_advanced_search` permission.

## Policy

One JSON `access` block decides which tools, Supabase schemas, Alexandria operations and markets, and Tavily extraction URLs are allowed. Cloud uses the tracked `config/policy.cloud.json`, baked into the image, so the deployed policy is whatever the deployed digest was built from; a change needs a rebuild and deploy. Local Compose mounts the ignored `config/policy.local.json` over it. There are no per-session assignments or expiry: every signed-in account gets the same policy.

## Budgets

Tavily and Firecrawl each have **50 credits per UTC day and 500 per calendar month**, shared by every client and tool for that provider. There is no per-session or per-tool cap.

- Credits are reserved atomically under a database lock, using database time, before the provider is called.
- A failed or unclear call keeps its reservation; nothing is retried or refunded automatically.
- Cache hits and free discovery spend nothing new. Cached responses last one hour and are kept per client.
- Changed or unknown Alexandria prices fail closed. If the database is unreachable, no provider call is made.
- Reconnecting or refreshing a token never resets the totals.

## Provider boundaries

| Provider | Credential | Restriction |
|---|---|---|
| Supabase | `SUPABASE_METADATA_DSN` | Dedicated `horology_agents` role with no table SELECT or DML; TLS `verify-full` against the official Supabase CA packaged at `/certs/supabase-ca.crt` |
| Tavily | `TAVILY_API_KEY` | Gateway-only key, with a dashboard limit as a second guard |
| Firecrawl | `FIRECRAWL_API_KEY` | Gateway-only key; URL policy `public_https` |

URLs supplied by agents must be public HTTPS. Local, private, link-local and metadata addresses, and DNS answers mixing public and private addresses, are refused (`horology_runtime.urls`). A local DNS check can't prove how the provider will resolve or redirect. Results are untrusted content; common token patterns are redacted on a best-effort basis. HTTP responses are size-bounded, redirects and environment proxies are off.

GitHub and Google Drive adapters were removed in favour of the platforms' own connectors, which this gateway doesn't police. They remain in Git history at commit `d643223`.

## Code layout

| Path | Does |
|---|---|
| `server.py` | Assembles the MCP server and sign-in |
| `integrations/{supabase,tavily,firecrawl}/` | `client.py` makes the fixed provider calls; `tools.py` registers the MCP tools |
| `shared/access.py`, `policy.py` | Policy checks and credit reservation |
| `shared/http.py`, `shared/text.py` | Bounded HTTP and output sanitising |
| `database/` | Psycopg 3 pool (at most 4 connections) and repositories for quotas, cache and OAuth |
| `config/` | Policy files |
| `scripts/` | Local set-up and `revoke_email.py` |

Database tables: [Data](../data/data-model.md). Setup and local use: the [gateway README](https://github.com/Welladino/Horology/blob/main/mcp-servers/mcp-gateway/README.md).
