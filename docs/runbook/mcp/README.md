# MCP Servers

Horology's two purpose-built MCP servers each expose a small, fixed set of named tools with their own credentials and their own container. Neither allows arbitrary code execution or arbitrary API access. How they work: [MCP architecture](../../architecture/mcp/README.md).

- [`document_graph_server.md`](document_graph_server.md) — the document graph: running, connecting and testing it locally.
- Gateway: setup, local start-up and verification are in the [gateway README](../../../mcp-servers/mcp-gateway/README.md).
- Cloud deployment of both: [`../gcp/mcp_deployment.md`](../gcp/mcp_deployment.md).

For starting, stopping and rebuilding these containers alongside Hermes, see [`running_all_services.md`](../docker/running_all_services.md).

## Adding a new MCP server

Pattern established by both servers:

1. `mcp-servers/<name>/` — `server.py` (the `mcp` Python SDK's `MCPServer`, `streamable-http` transport), `requirements.txt` with exact pins, a `Dockerfile` built from the repository root that installs `shared-runtime/`, and runs as a non-root user.
2. Its own `compose.yaml` (own Compose project), publishing at most a `127.0.0.1` port, credentials only in its own private `.env`. An optional `compose.hermes-network.yaml` joins `horology_default` for Hermes.
3. Add the source folder to the root `.dockerignore` allowlist, and the image to `cloudbuild.yaml` and `scripts/ci/check_image.py`.
4. Verify in isolation before connecting anything: reachable only where intended.
5. Connect Hermes with `hermes mcp add <name> --url http://<service-name>:<port>/mcp` (add `-p <profile>`; connections are per profile).
6. Document it here and in [`docs/architecture/mcp/`](../../architecture/mcp/README.md).
