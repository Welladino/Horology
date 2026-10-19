# Gateway provider scope: Alexandria and extraction added, GitHub and Google removed

## Topic
- gateway-provider-scope

## Context

After the first deployment, the operator approved switching on more of the Agent Register's disabled capabilities (excluding DataForSEO), and planning deliverables needed a home. The gateway at that point had GitHub reads, Google Drive/Docs/Sheets adapters in progress and an optional GitHub planning-note writer.

## Decisions

**Fixed Alexandria reads and Tavily extraction (2026-10-12).** Free catalogue discovery for Shopify, Alibaba and trends; global Shopify search (at most five) and product details; Alibaba first-page search and listing details (mostly sponsored, no stock claim); trends interest over time for 1–5 terms. Product IDs must come from the same client's recent search. Each paid Alexandria call re-checks the free catalogue price (5 credits per call, not per record) and reserves before running. Tavily extraction reads 1–5 approved public HTTPS URLs for 1 credit, with private IPv4 and IPv6 targets refused. Contracts were confirmed through free discovery (catalogue `sha256:07a08dba…`). Build `7d73cbd5` passed with 85 tests and was deployed as `mcp-gateway-00008-kqw`; the private Horology plugin went to 1.0.2 with an updated skill. Paid Alexandria and Tavily calls were not live-tested.

**Planning deliverables are Google Docs, not GitHub files (2026-10-12).** Plans became draft Google Docs in the domain's planning folder from the Location Directory, so the create-only GitHub writer was removed; research keeps read-only GitHub. Google adapters were built and verified locally against private copies of the registers: template copy, revision-controlled edits, idempotent replays through durable receipts, and bounded register tools that could update only investigation fields, index owned drafts and propose decisions, never founder fields. The operator chose the Sheets scope with gateway-side restrictions. A test client timed out after a copy had succeeded, and the receipt returned the existing document on retry instead of making a second copy.

**Native connectors instead (2026-10-13).** The operator chose to evaluate the platforms' own GitHub and Google connectors. The GitHub and Google adapters, their tests, migration and settings were moved to `placeholders/connectors/` and then deleted from the active tree on 2026-10-13 (last present in commit `d643223`). Retired provider settings sit in the ignored `placeholders/connectors/.env.local`. Granting a retired tool now fails policy start-up, and the image contract checks neither adapter is packaged. The gateway kept 13 tools. Native connectors' permissions and usage are outside the gateway's policy and budgets.

**Any public HTTPS page for Firecrawl scrape (2026-10-13).** The operator authorised scraping any public HTTPS URL rather than an exact list, under JSON `firecrawl.url_policy=public_https`. URL and address checks moved to `shared-runtime/horology_runtime/urls.py`: localhost and internal names, private, link-local, multicast and non-global addresses, embedded private IPv4, odd ports, userinfo, whitespace and fragments are refused, and every resolved address must be public. Legitimate public 172.x and 169.x addresses are allowed; only 172.16/12 and 169.254/16 are refused. Tavily extraction keeps exact URL approval. JSON policy, not the Agent Register's access IDs, is the source of permissions.

## Rationale

Fixed, priced contracts instead of arbitrary provider execution; and one place (Drive, through the platform's own connector) for planning deliverables instead of a second writer into GitHub.

## Impact

- Current tools and boundaries: [gateway](../../architecture/mcp/gateway.md). Hermes' gateway tool filter still names the removed GitHub tools ([known gap](../../architecture/hermes/hermes-agents.md#known-gaps)).

## Follow-Ups

- DataForSEO stays future work.
- Verify paid Alexandria and Tavily calls live within budget.
- Local DNS checks can't control how Firecrawl or Tavily resolve or follow redirects.
