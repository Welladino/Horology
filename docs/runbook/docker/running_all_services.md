# Run the local services

Horology's optional local stack has two Docker Compose projects: the document graph and the restricted gateway. They can run by themselves or join the external `horology_default` network used by the separately maintained Watchmaker Hermes deployment.

Use this page for everyday start, health, log and stop commands. Use the component runbooks for first-time credentials and deeper troubleshooting:

| Need | Use |
| --- | --- |
| Start or stop both Horology MCP services | This page |
| Configure graph credentials, clients or local sync | [Document graph](../mcp/document_graph_server.md) |
| Configure gateway credentials, policy or smoke tests | [Gateway](../mcp/gateway_server.md) |
| Configure or operate Hermes | [Watchmaker handoff](hermes_setup.md) |

## Before you start

Install Docker Desktop or Docker Engine with Compose v2. Prepare the ignored service files described in the two component runbooks:

- `mcp-servers/document-graph/.env` for Neon and embedding settings;
- `mcp-servers/mcp-gateway/.env.local` and `config/policy.local.json` for the gateway.

The root `.env` is only for repository-level operator commands such as Alembic. Do not move service credentials into it.

## Start both services

If Hermes must reach them, create the shared network once. An "already exists" response is harmless.

```bash
docker network create horology_default
```

Then start each service with its Hermes network overlay:

```bash
docker compose \
  -f mcp-servers/document-graph/compose.yaml \
  -f mcp-servers/document-graph/compose.hermes-network.yaml \
  up -d --build

docker compose \
  -f mcp-servers/mcp-gateway/compose.yaml \
  -f mcp-servers/mcp-gateway/compose.hermes-network.yaml \
  up -d --build
```

Without Hermes, omit each `compose.hermes-network.yaml` file. Each service then uses its own private Compose network while retaining its loopback-only host port.

## Check health and endpoints

```bash
docker compose -f mcp-servers/document-graph/compose.yaml ps
docker compose -f mcp-servers/mcp-gateway/compose.yaml ps
```

| Service | Host address | Address from Watchmaker |
| --- | --- | --- |
| Document graph MCP | `http://127.0.0.1:8765/mcp` | `http://document-graph-mcp:8765/mcp` |
| Gateway MCP | `http://127.0.0.1:8767/mcp` | `http://horology-mcp-gateway:8767/mcp` |

Both host ports are loopback-only. Do not publish them on a public interface.

## Read logs

```bash
docker compose -f mcp-servers/document-graph/compose.yaml logs --tail=100 document-graph-mcp
docker compose -f mcp-servers/mcp-gateway/compose.yaml logs --tail=100 gateway
```

Add `-f` after `logs` to follow output. Press Ctrl-C to stop following; it does not stop the container.

## Stop and remove the service containers

Use the same file combination used for `up`:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml down
docker compose -f mcp-servers/document-graph/compose.yaml -f mcp-servers/document-graph/compose.hermes-network.yaml down
```

If you started a service without the Hermes overlay, omit that overlay from its `down` command too. These commands do not remove ignored configuration files, Neon data, the external network, or Watchmaker's Hermes state and workspace volume.

Remove the shared network only after Watchmaker and both MCP projects are stopped and only when it is no longer needed:

```bash
docker network rm horology_default
```

## Troubleshooting

- **External network not found:** run `docker network create horology_default`, then repeat the overlay `up` command.
- **Port already in use:** use the matching `docker compose ... ps` command to locate the old project, then stop that exact project.
- **Hermes cannot reach a service:** recreate that service with both its base file and `compose.hermes-network.yaml`.
- **Configuration changed but behavior did not:** rebuild the affected MCP image.
- **A service exits immediately:** inspect its logs and confirm its own ignored environment file exists.
