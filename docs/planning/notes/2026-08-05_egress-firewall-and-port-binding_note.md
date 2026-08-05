# Implementation Note

## Topic
- egress-firewall-and-port-binding

## Context

After the Docker gateway was up and running, reviewed the running setup for security gaps before adding more capabilities (skills, cron, more provider keys).

## Decision

**Port binding: localhost-only**

`docker-compose.yml` originally published ports as bare `8642:8642` / `9119:9119`, which Docker binds to `0.0.0.0` by default — reachable from anything on the local network, not just this machine. Port `8642` (the OpenAI-compatible API) has no auth by default, making this the more serious of the two exposures. Fixed by binding explicitly: `127.0.0.1:8642:8642` / `127.0.0.1:9119:9119`. Verified via `docker port horology-hermes` after recreate.

**Egress firewall (iron-proxy): enabled**

Hermes ships an optional, disabled-by-default egress firewall (`hermes egress`) — a local TLS-intercepting proxy that swaps opaque proxy tokens for real API credentials only at the network edge, so the agent's own context/session never holds raw provider keys. It also allowlists outbound domains (HTTP 403 to anything not explicitly allowed, before any bytes leave the host) and is Docker-enforced.

Chose to enable this now rather than defer, since the agent will do autonomous web research/scraping and the risk (prompt-injected content on a scraped page inducing an outbound exfiltration request) is real once that capability exists — easier to build in from the start than retrofit after more keys/tools are added.

Setup performed:
```
docker exec horology-hermes hermes egress install   # binary, SHA-256 verified
docker exec horology-hermes hermes egress setup      # CA cert, token minting, config
docker exec horology-hermes hermes egress start       # daemon, port 9090, Docker-enforced
```
OpenRouter's key was auto-detected and minted into a proxy token (`openrouter-c…4a4e`) mapped to `openrouter.ai, *.openrouter.ai`. Verified working end-to-end with a live test query (`hermes chat -q "..."`), confirming model calls succeed through the proxy, not just that the daemon is running.

Any new provider/API key added later (GitHub, Neon, GCP, search tools) should go through the same `hermes egress setup` re-run so it gets minted into the proxy rather than sitting as a raw env var.

**Port/DB clarifications (from user questions)**

- No conflict with `Article_aggregator_agent`'s local dev ports: `127.0.0.1` is a shared address, not a shared namespace — collisions are per-port, not per-address. NLE's typical dev ports (~8000, ~5173) don't overlap with Hermes's 8642/9119; confirmed via `lsof`.
- Hermes's own `state.db` (SQLite, in `hermes-data/`) does **not** replace the planned Neon doc-graph DB. It stores Hermes's own conversational/operational state (`sessions`, `messages`, `messages_fts`, `session_model_usage`, `async_delegations`, `gateway_routing`) plus separate `kanban.db`/`projects.db` for its built-in task-board features. It is SQLite (not Postgres), single-machine, schema-owned by Hermes itself (not safe to bolt custom tables onto), and semantically conversation logs rather than structured business documents. The doc graph (`documents`/`document_links`/`run_log`, versioned, cross-linked, queryable from any repo via MCP) remains a separate, purpose-built store.

## Rationale

Both changes follow the same principle already established: keep the blast radius of any one credential or exposure as small as possible, and verify claims (port binding, proxy functioning, what a DB actually contains) rather than assume. Enabling egress now, while only one provider key exists, is cheap; retrofitting it after several more keys and an active cron schedule are in place would be more disruptive.

## Impact

- All future provider/tool API keys should be added through `hermes egress setup` (re-run, or check it auto-detects), not left as bare env vars, to stay consistent with this protection.
- Confirms Neon setup is still needed and not made redundant by anything Hermes ships internally.

## Follow-Ups

- None outstanding; both changes verified working, not just configured.
