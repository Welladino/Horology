# Restricted MCP read capability expansion

Date: 2026-10-12

## Scope and decisions

Operator approved expanding disabled capabilities first, excluding DataForSEO. Google provider work was subsequently deferred, and the optional GitHub planning-note writer must remain disabled until revisited with Google. No Google API enablement or provider OAuth was performed; started Google changes were removed.

Operator confirmed two paid Firecrawl calls per assignment, with Alexandria costing 5 credits and basic scrape costing 1. Assignment credit cap is 10 to permit two Alexandria calls; daily/monthly limits remain 50/500. Existing assignment IDs, expiry and spending history must be preserved on rollout. No reconnect or policy update resets usage.

## Implementation

- Fixed free catalogue discovery for Shopify, Alibaba and trends; no arbitrary capability execution.
- Global Shopify search (max five) and product details; assigned markets only. Product IDs must come from this assignment's search within the one-hour cache lifetime.
- Alibaba first-page search (five returned records) and listing details; exact published URL format and assignment-local recent result proof. Search is mainly sponsored placements, with no verified stock claim.
- Trends interest-over-time: 1–5 terms, approved country, fixed web property and bounded supported periods. Large provider results carry a truncation marker.
- Each paid Alexandria call verifies the current free catalogue price (5 fixed credits, not per record), then reserves budget before execution. No automatic retries. Successful results share existing assignment-scoped cache semantics.
- Tavily basic extraction: 1–5 exact approved public HTTPS URLs; 1-credit reservation, 20-second provider timeout, bounded sanitized content. Private/reserved IPv4 and IPv6 targets are rejected. Remote provider redirects/DNS remain outside local validation's guarantee.
- Optional GitHub create-only writer adapter uses a separate GITHUB_WRITE_TOKEN and exact approvals. It remains unassigned and unconfigured; no branches, files or remote commits created. Branch behavior should be revisited with the Google workflow before enabling.

Initial example markets are SG/US. No storefront or worldwide scope is assumed. Examples are configuration templates, not proof of live provider execution.

## Verification

85 mocked/database tests passed using disposable PostgreSQL; native MCP smoke passed with 25 listed tools, valid authentication and denied unauthenticated/invalid-auth/out-of-scope calls. Gateway dependency audit found no known vulnerabilities. Application Docker stacks were not restarted. Cloud Build/scans and cloud rollout are recorded below when completed. No paid provider calls performed during preparation.

## Provider contracts

Verified through the Firecrawl plugin's free discovery (0 credits): shopify/catalog/search_catalog, shopify/catalog/get_product, alibaba/retail/search, alibaba/retail/product and firecrawl-trends/trends/interest_over_time. Catalogue version: sha256:07a08dba25eb7983ea0806b7b1ea009dc2f6bff1e102a1e28cb2ba725ce00121.

Sources: https://docs.firecrawl.dev/api-reference/endpoint/scrape ; https://www.firecrawl.dev/alexandria/shopify ; https://docs.tavily.com/documentation/api-credits ; https://docs.tavily.com/documentation/api-reference/endpoint/extract ; https://docs.github.com/en/rest/repos/contents .

## Next work

Google and GitHub writer activation deferred at operator request. DataForSEO deferred. After read-provider rollout, verify the actual scheduled runtime, then separate login identity from per-run assignments. Document-graph access and Document Index logic remain later work.

## Cloud rollout and instruction update

- Cloud Build 7d73cbd5-423c-4c29-bd45-64ac209228f5 succeeded: 85 tests passed, 9 expected local Docker-stack skips, dependency audits/source scans/image gates passed. Both rebuilt images report 44 unfixed HIGH Debian findings and 0 CRITICAL. No fixable HIGH/CRITICAL findings passed through the release gate; Trivy remains 0.75.0. These reports cover new candidates, not a rescan of every older deployed image.
- Operator explicitly approved the live service update after automatic approval review initially blocked it. Gateway revision mcp-gateway-00008-kqw now serves image sha256:2fce0a9483aa16281a0c501c15bbe7f7ab19f698ed923bc809bab38e944ea46f and policy secret version 4. Existing OAuth, service account, other secrets, ingress and assignment IDs/expiry remain unchanged. Document-graph candidate built but not deployed.
- Existing native MCP OAuth gateway_status verified the new approved tools and disabled Google/writer/DataForSEO IDs. Public OAuth discovery returns 200; anonymous and invalid-token MCP return 401. Current host tool inventory may need a refresh to expose new names. Scheduled-runtime unattended behavior remains unverified.
- One direct free Alexandria catalogue call using the gateway's existing key succeeded and returned all five expected 5-credit contracts. Paid Shopify/Alibaba/trends/Tavily execution was not live-tested; previous assignment spending was not reset to manufacture test allowance.
- Updated deployed-current through Artifact Registry tags.patch with existing restricted tags.update permission. gcloud artifacts docker tags add attempted delete/recreate and failed without tags.delete; IAM was not broadened.
- Updated Agent Register MCP cells for IDs 1–7, 17–18 and 21, preserving formats and surrounding values. Status distinguishes deployed adapters from unverified paid execution.
- Published private Horology plugin 1.0.2, release pluginrel_6accc08041f0819195ce29023943ab84, with updated operating skill. App binding/presentation unchanged; published readback and skill validation passed. Host automatic skill refresh remains separately unverified.
- No commit or push performed in this follow-up.
