# MCP Servers

Horology's own purpose-built MCP servers — each exposes a small, fixed set of named tools against one external system, with its own credential and its own container. None expose arbitrary code execution or arbitrary API access; see each doc for the specific tools and the reasoning behind that boundary.

- [`document_graph_server.md`](document_graph_server.md) — Neon Postgres: write/read/link business documents (recommendations, content, analysis, reports).
- [`github_monitor_server.md`](github_monitor_server.md) — read-only GitHub monitoring for `Article_aggregator_agent`: CI status, PRs, Dependabot alerts, code search.

For starting/stopping/rebuilding these containers alongside Hermes itself, see [`docs/runbook/docker/running_all_services.md`](../docker/running_all_services.md).

## Adding a new MCP server

Pattern established by both servers above:

1. `mcp-servers/<name>/` — `server.py` (using the `mcp` Python SDK, `MCPServer` class, `streamable-http` transport), `requirements.txt` (pin exact versions), `Dockerfile` (matches local dev Python).
2. Add a service to `docker-compose.yml` — **no `ports:` mapping**, credential(s) only in that service's own `environment:`, never shared with `hermes`'s environment.
3. Verify in isolation before connecting anything: `curl` from the host (should fail), `curl` from inside another container on the same network (should succeed).
4. Connect via `hermes mcp add <name> --url http://<service-name>:<port>/mcp` (add `-p <profile>` for a specific subagent — connections are per-profile, not shared).
5. Write a doc here following the same shape: what it exposes, the credential and its scope, how to run/test/connect it.
