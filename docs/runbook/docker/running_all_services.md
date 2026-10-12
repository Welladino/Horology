# Running Horology services

Hermes, document-graph and the restricted gateway each have their own Compose project. From the repository root, ensure the shared `horology_default` network exists, start Hermes, then attach the separate MCP servers:

```bash
# First setup only, if the network does not already exist:
docker network create horology_default
# First setup or an intentional Hermes image update:
docker pull nousresearch/hermes-agent:latest

docker compose up -d
docker compose -f mcp-servers/document-graph/compose.yaml -f mcp-servers/document-graph/compose.hermes-network.yaml up -d --build
```

Root `.env` supplies Hermes configuration; document-graph loads `mcp-servers/document-graph/.env`. Docker Desktop shows `horology-hermes` (Hermes only) and `horology-document-graph-mcp` separately. Document data remains in Neon.

For document-graph without Hermes, use only its base Compose file:

```bash
docker compose -f mcp-servers/document-graph/compose.yaml up -d --build
```

The base file uses its own network with port 8765 published only on localhost. Include `compose.hermes-network.yaml` whenever recreating it with Hermes connectivity.

Once the main network exists, start the restricted gateway with Hermes connectivity:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml up -d --build gateway
```

Use both gateway Compose files for later recreations if Hermes connectivity is needed. Its private .env.local and policy.local.json configure authentication and provider access. Set GATEWAY_DATABASE_URL to the dedicated Neon gateway login; quota history lives in Neon and survives container recreation. Local monitoring assignments expire after 24 hours; scheduled assignment provisioning remains pending.

Document graph publishes `127.0.0.1:8765`; laptop clients such as Codex connect to `http://127.0.0.1:8765/mcp`. Hermes continues to use `http://document-graph-mcp:8765/mcp` on the shared Docker network. Hermes connects to the authenticated gateway at http://horology-mcp-gateway:8767/mcp. The gateway also publishes localhost port 8767 for local test clients.

The `horology-hermes` Compose project and container use the official `nousresearch/hermes-agent:latest` image directly. Pull that image for an intentional upstream update. The shared network is external to the Compose projects, so stopping one project does not remove it.
