# Local Docker: three independent Compose projects

## Topic
- local-compose-projects

## Context

Hermes and both MCP servers had grown up in one root Compose project, so they couldn't be started, stopped or rebuilt independently, and laptop MCP clients such as Codex couldn't reach the local document graph.

## Decisions

**Document graph in its own project (2026-10-12).** `horology-document-graph-mcp` uses `mcp-servers/document-graph/compose.yaml`. An optional `compose.hermes-network.yaml` joins the Hermes network `horology_default` as `document-graph-mcp`. The full-stack test fixture starts both projects and waits for HTTP readiness, which removed a start-up race. A bounded invalid JSON-RPC POST from Hermes returned the expected 400.

**Localhost port for laptop clients (2026-10-12).** The document graph publishes `127.0.0.1:8765` only; laptop clients use `http://127.0.0.1:8765/mcp`, Hermes keeps the network name. The local copy has no sign-in and includes write and paid-embedding tools, which is why it must never bind beyond localhost. A test asserts the exact binding, and a host client discovered the tools without calling any.

**Hermes project renamed (2026-10-12).** The root project is `horology-hermes`, with container `horology-hermes` and the upstream image tagged locally `horology-hermes:latest`. `horology_default` is an external network, so MCP overlays keep working whatever the project is called.

The gateway already ran as its own `horology-mcp-gateway` project on `127.0.0.1:8767`. 78 tests passed after each change.

## Rationale

Each component can be started, stopped and rebuilt on its own, Docker Desktop shows three clear groups, and nothing listens beyond localhost.

## Impact

- Current layout: [Hermes containers](../../architecture/hermes/README.md#containers). Commands: [running all services](../../runbook/docker/running_all_services.md).
