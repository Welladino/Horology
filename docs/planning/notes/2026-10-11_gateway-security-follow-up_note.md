# Gateway security follow-up

## Scope

Proportionate checks for a founder-owned gateway used by scheduled agents. This records outstanding work; it does not claim cloud readiness or implement new controls. Exhaustive IPv6, DNS-rebinding and remote Firecrawl-fetch investigations are deferred.

## Existing verification

Sixteen mocked regression tests cover assignment expiry, tool authorization, repository allowlists, path traversal, Drive file/range scope, Supabase project/role/auth-schema restrictions and parameterized read-only queries, shared atomic paid quotas and persistence, assignment cache isolation, Firecrawl URL approval/private-address denial, and Tavily auto-upgrade prevention. The running-container smoke verifies MCP authentication, thirteen-tool discovery and scope denial. Compose publishes the gateway only on localhost.

## Before deployment

- Extend mocked Firecrawl address checks with representative localhost, private-network and cloud metadata addresses. Verify approved public targets succeed and unapproved URLs fail without upstream calls. No real requests to internal or metadata endpoints.
- Preserve fixed provider origins, response limits, disabled redirects/environment proxies, strict Supabase TLS, read-only credentials, and secret exclusions during changes.
- Decide supported agent clients and authentication. Local bearer credentials are an expiring prototype; cloud OAuth/client integration remains unimplemented.
- Supply provider credentials through Secret Manager. Provision separate least-privilege assignments per agent, with explicit tools, repositories and paid budgets.
- Replace the local SQLite quota-store deployment assumption with a durable store suitable for the chosen cloud concurrency model before scaling. Keep reservations atomic across instances.

## At GCP deployment

- Choose Cloud Run ingress and service IAM deliberately based on client compatibility; private network ingress is not assumed compatible with subscription-agent clients. Public network reachability and authenticated tool access are separate properties.
- Test actual deployed MCP URL externally: absent and invalid credentials denied, expired assignments denied, authorized client succeeds, unauthorized tools/repositories denied. Check HTTP streaming/client compatibility.
- Verify Cloud Run service ingress, IAM, any custom-domain/load-balancer path and alternate service URL obey the intended access policy. No unauthenticated tool execution.
- Verify outbound Supabase verify-full with the bundled CA and secret injection; ensure logs omit tokens, passwords and raw DSNs.

No GCP resources, IAM changes or deployment were performed.
