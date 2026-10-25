# Restricted gateway (local)

The gateway exposes fixed, policy-controlled Supabase metadata, Tavily, Firecrawl/Alexandria and private Pages publishing tools. It never receives a general provider API or SQL operation. Architecture and current tool boundaries: [Gateway](../../architecture/mcp/gateway.md).

This page is the gateway-specific setup and troubleshooting guide. Use [Run all local services](../docker/running_all_services.md) for the normal three-project start/stop sequence; return here when creating gateway credentials, changing policy, applying its database migration or running its smoke test.

## First-time setup

From the repository root:

```bash
.venv/bin/python mcp-servers/mcp-gateway/scripts/setup_local_gateway.py
```

The initializer creates ignored files and refuses to overwrite them:

- `mcp-servers/mcp-gateway/.env.local`;
- `mcp-servers/mcp-gateway/config/policy.local.json`;
- `tests/manual/gateway/fixtures/private/client.local.json`.

Fill the runtime values in `.env.local`. Use the dedicated `horology_gateway` Neon pooled connection for `GATEWAY_DATABASE_URL`; provider keys belong here, not in policy JSON or the root `.env`. Cloudflare tokens are needed only for `publish_synthesis`.

Apply database migrations with the owner `DATABASE_URL`, not the gateway runtime login:

```bash
.venv/bin/alembic upgrade head
```

## Start

With Hermes already running:

```bash
docker compose \
  -f mcp-servers/mcp-gateway/compose.yaml \
  -f mcp-servers/mcp-gateway/compose.hermes-network.yaml \
  up -d --build
```

Without Hermes:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml up -d --build
```

The host endpoint is `http://127.0.0.1:8767/mcp`. Keep the loopback binding: local clients use a bearer credential and do not have the cloud Google sign-in boundary.

## Verify

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml ps
docker compose -f mcp-servers/mcp-gateway/compose.yaml logs --tail=100 gateway
```

Run the existing-client smoke check, which calls status and does not spend provider credits:

```bash
.venv/bin/python tests/manual/gateway/smoke.py --existing
```

## Stop

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml down
```

If it was started without the Hermes overlay, use only the base file for `down`.

## Safety notes

- Never use a Supabase service-role key or a Postgres owner login for runtime metadata reads.
- Policy changes require a rebuild. Cloud uses the policy baked into the deployed image; local Compose mounts `policy.local.json`.
- Tavily and Firecrawl quotas are shared across clients. Failed or ambiguous calls retain their reservations.
- A local or cloud credential does not automatically authorize Pages publishing; that operation also checks the workspace project and Cloudflare Access configuration.
- Cloud deployment, OAuth and secrets are covered by the [deployment runbook](../gcp/mcp_deployment.md).
