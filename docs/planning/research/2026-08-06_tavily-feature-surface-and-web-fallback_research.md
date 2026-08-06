# Research Brief

## Topic
- tavily-feature-surface-and-web-fallback

## Question
- Tavily (the web search provider configured as Hermes's `web.backend`) has more product surface than basic search — Crawl, Map, Sheets, Company Researcher, Market Researcher. Does Horology's current setup use any of these? And separately: does Hermes have any fallback if the configured web search backend (Tavily) fails?

## Summary
- Current setup only uses Tavily's `search` and `extract` endpoints, via Hermes's generic `web_search`/`web_extract` tools — confirmed by directly querying a running profile for its available `web_`-prefixed tools.
- Tavily's Crawl and Map are real API endpoints on the same key, but **Hermes's `web` toolset doesn't expose them at all**, regardless of backend — the abstraction only ever maps to search+extract.
- "Sheets," "Company Researcher," and "Market Researcher" are not API features — they're separate open-source client applications/agent templates Tavily publishes on GitHub, built on top of the Search/Extract API. Not something togglable via config.
- Hermes has **no fallback mechanism for web search** — unlike its LLM layer (`fallback_providers`/`fallback_model`, already configured for us with GLM-5.2), a failing/rate-limited search backend has no automatic failover to another provider.

## Sources
- Hands-on: `hermes chat -q "List every tool you have that starts with web_..."` against a running profile — confirmed exactly two tools (`web_search`, `web_extract`), no crawl/map/sheets-related tool.
- [Tavily Crawl endpoint docs](https://docs.tavily.com/documentation/api-reference/endpoint/crawl)
- [Tavily Map endpoint docs](https://docs.tavily.com/documentation/api-reference/endpoint/map)
- [Tavily product page](https://www.tavily.com/product)
- [tavily-sheets (GitHub)](https://github.com/tavily-ai/tavily-sheets)
- [tavily_company_researcher (GitHub)](https://github.com/tavily-ai/tavily_company_researcher)
- [market-researcher (GitHub)](https://github.com/tavily-ai/market-researcher)
- [Hermes Agent web-search feature docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-search)
- [NousResearch/hermes-agent web-search.md source](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/web-search.md)

## Findings
- **Tavily's full API surface** (one unified REST API, same key, different endpoint paths): `search`, `extract`, `map` (structured site-URL traversal, no content), `crawl` (map + extract combined — "crawl2rag" is Tavily's descriptive name for this, not a separate endpoint), and a `research` endpoint for multi-step deep-research reports. Keyless/free access is limited to `search`/`extract` only; crawl, map, and research require the signed-up API key we already have.
- **Sheets / Company Researcher / Market Researcher** are separate, open-source, client-side projects (LangGraph agent templates or a spreadsheet-filling app), not API endpoints. Adopting one of these would mean bringing in or adapting that project's own code, not flipping a config flag.
- **Hermes's `web` toolset abstracts across many backends** (Tavily, Firecrawl, SearXNG, Brave, DDGS, Exa, Parallel, xAI) via `web.backend` (or split `web.search_backend`/`web.extract_backend`), but regardless of which backend is chosen, only `web_search`/`web_extract` are ever exposed — Tavily's crawl/map capability is simply not wired into Hermes.
- **No `web.fallback_backend` or equivalent found** in Hermes's config reference. Backend selection is static config (or credential-presence auto-detection at startup), not runtime failover — asymmetric with the LLM layer, which does support `fallback_providers`. If Tavily errors or rate-limits, there's no documented automatic switch to another provider; would require manually editing `config.yaml` and restarting.
- Not exhaustively ruled out: undocumented retry/backoff-only behavior inside Hermes's Python source (distinct from true multi-provider failover) — docs review only, no source-code grep, for this pass.

## Recommendation
- No action needed now — current usage (search + extract only) already covers what Horology's subagents need.
- If a future subagent needs deep site crawling (e.g. a research-heavy role wanting to ingest a whole competitor site or documentation set into RAG-ready chunks), build a small purpose-built MCP server wrapping Tavily's `/crawl` and `/map` endpoints — same narrow-tool pattern as `document-graph-mcp`/`github-monitor-mcp`, not adopting Hermes's generic `web` toolset (which structurally can't reach them).
- Treat Tavily as a single point of failure for web search until/unless a manual-switch runbook step (or a custom fallback wrapper) is built — not urgent at current usage levels, but worth remembering if Tavily has an outage during a real scheduled run.

## Open Questions
- Whether Hermes's Python source has any undocumented retry/backoff behavior for web search failures, distinct from true provider failover (not checked, doc-review only).
- Whether a future subagent's role will actually need Crawl/Map/deep-research capability — no concrete need identified yet.
