# Running Horology services

From the repository root, start Hermes and the separate document graph:

```bash
docker compose build document-graph-mcp
docker compose up -d
```

Root .env supplies Hermes configuration; document graph loads mcp-servers/document-graph/.env. The retired github-monitor service is no longer present.

Once the main network exists, start the restricted gateway with Hermes connectivity:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml up -d --build gateway
```

Use both gateway Compose files for later recreations if Hermes connectivity is needed. Its private .env.local and policy.local.json configure authentication and provider access. Preserve the gateway-state volume: recreating containers must not reset quotas. Local monitoring assignments expire after 24 hours; scheduled assignment provisioning remains pending.

Document graph has no published host port; Hermes connects at http://document-graph-mcp:8765/mcp. Hermes connects to the authenticated gateway at http://horology-mcp-gateway:8767/mcp. The gateway also publishes localhost port 8767 for local test clients.
