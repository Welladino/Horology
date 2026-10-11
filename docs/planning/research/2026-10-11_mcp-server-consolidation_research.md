# Research Brief

## Topic
MCP server consolidation

## Question
Can github-monitor be retired in favour of the restricted gateway, and should document-graph join that gateway?

## Summary
- GitHub consolidation is the preferred direction, but the gateway is not yet a complete replacement for Code Sentinel.
- Keep document-graph as a separate service and candidate for a separate Cloud Run deployment.
- Current local Hermes connections differ from subscription-agent gateway assignments; changing personas alone is insufficient.

## Sources
- mcp-servers/github-monitor/server.py
- mcp-servers/mcp-gateway/integrations/github/client.py and tools.py
- personas/subagents/code-sentinel.md
- docker-compose.yml and docs/runbook/mcp/README.md
- mcp-servers/document-graph/server.py
- tests/mcp_servers/test_github_monitor.py and tests/test_docker_stack.py

## Findings
The old monitor exposes repo status, recent commits with author/date/message, latest branch CI status, open PRs, diffs, file reads, Dependabot alerts and code search. The gateway exposes bounded files, trees, search, PR file patches and generic issue/PR/commit/workflow records. It does not expose Dependabot alerts or repo health metadata. Generic commit records omit nested commit messages/dates/authors; workflow records omit names and branch selection. PR patches are capped at twenty files and truncated, unlike a full diff. These differences must be explicit in the persona so truncated evidence is not treated as complete.

Code Sentinel currently uses the old monitor for Article_aggregator_agent only. Preserve this profile's narrower repository scope even though the global gateway allows Horology too. Source personas are under personas/; hermes-data is ignored runtime state. Hermes MCP connections are profile-specific. Never edit live config.yaml directly; use the documented Hermes CLI approach. Existing installed skills may need review and re-distribution; do not rewrite ignored runtime logs/caches or historical notes.

The main Compose stack still starts github-monitor-mcp and document-graph-mcp on an internal network. The gateway currently runs through its own Compose project and authenticates clients with expiring assignments. Migration requires working connectivity between Hermes and the authenticated gateway, fresh per-run assignments suitable for recurring monitoring, and profile connection updates. Reusing an exhausted local test assignment would fail.

Document-graph provides seven narrow tools for reading/writing/linking Neon business documents and paid OpenRouter embeddings. It serves Hermes output persistence; subscription-agent outputs currently use Drive/Sheets. It has no application authentication visible in server.py and relies on internal Compose network isolation. A public Cloud Run deployment therefore requires authentication/access policy before exposure, secret injection, bounded embedding usage and compatible clients. Do not assume its current image is safe to expose publicly as-is.

## Recommendation
Consolidate GitHub implementation into the gateway after closing required capability gaps and verifying authenticated Hermes connectivity. Then update Code Sentinel source persona, relevant skill instructions/distribution and MCP profile connections; remove the old Compose service, server and obsolete tests; update current architecture/runbooks; run the full repository tests and a real read-only Hermes check. Keep historical notes. Retirement is pending; the old service remains intact.

Keep document-graph separate under mcp-servers/document-graph. A separate Cloud Run service preserves Neon write/embedding credentials and independently deployable lifecycle. Add cloud authentication and embedding limits before deploying. No need for an extra public-facing proxy or integration in the gateway until a concrete client requires a single endpoint.

## Open Questions
- Verify Hermes authenticated streaming MCP support and assignment provisioning/renewal for recurring runs.
- Confirm minimal bounded GitHub monitoring additions and persona treatment of partial evidence.
- Locate actual installed GitHub skill instructions and determine which are used before modifying/distributing them.
- Choose document-graph clients, authentication and embedding budgets at deployment time.
