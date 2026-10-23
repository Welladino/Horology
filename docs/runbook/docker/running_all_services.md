# Run all local services

Horology's local stack is three independent Docker Compose projects joined to one external network. Run commands from the repository root. Root `docker compose` manages Hermes only.

This is the day-to-day orchestration page for starting, checking and stopping the complete stack. Component runbooks contain first-time configuration and deeper recovery:

| Need | Use |
| --- | --- |
| Start or stop Hermes, document graph and gateway together | This page |
| Configure or troubleshoot Hermes itself | [Hermes setup](hermes_setup.md) |
| Configure graph credentials, clients or a local sync | [Document graph](../mcp/document_graph_server.md) |
| Configure gateway credentials/policy or run its smoke test | [Gateway](../mcp/gateway_server.md) |

## Before you start

You need Docker Desktop or Docker Engine with Compose v2.

Prepare the private configuration:

- root `.env` for the Hermes dashboard, host UID/GID and the optional read-only sweep connection;
- `hermes-data/.env` for the model/provider settings created by Hermes setup;
- `mcp-servers/document-graph/.env` for its Neon and embedding settings;
- `mcp-servers/mcp-gateway/.env.local` and `config/policy.local.json` for the gateway.

Follow [Hermes setup](hermes_setup.md), [document-graph setup](../mcp/document_graph_server.md) and [gateway setup](../mcp/gateway_server.md) the first time.

## Start everything

Create the shared network once. The command reports an error if it already exists; that is harmless.

```bash
docker network create horology_default
```

Start Hermes:

```bash
docker compose up -d
```

Start the document graph with its Hermes network attachment:

```bash
docker compose \
  -f mcp-servers/document-graph/compose.yaml \
  -f mcp-servers/document-graph/compose.hermes-network.yaml \
  up -d --build
```

Start the gateway with its Hermes network attachment:

```bash
docker compose \
  -f mcp-servers/mcp-gateway/compose.yaml \
  -f mcp-servers/mcp-gateway/compose.hermes-network.yaml \
  up -d --build
```

Docker Desktop shows three projects: `horology-hermes`, `horology-document-graph-mcp` and `horology-mcp-gateway`.

## Check that they are healthy

```bash
docker compose ps
docker compose -f mcp-servers/document-graph/compose.yaml ps
docker compose -f mcp-servers/mcp-gateway/compose.yaml ps
```

Expected local endpoints:

| Service | Host address | Hermes address |
| --- | --- | --- |
| Hermes dashboard | `http://127.0.0.1:9119` | — |
| Document graph MCP | `http://127.0.0.1:8765/mcp` | `http://document-graph-mcp:8765/mcp` |
| Gateway MCP | `http://127.0.0.1:8767/mcp` | `http://horology-mcp-gateway:8767/mcp` |

Both MCP ports are published on loopback only. Do not change them to a public interface.

## Read logs

```bash
docker compose logs --tail=100 hermes
docker compose -f mcp-servers/document-graph/compose.yaml logs --tail=100 document-graph-mcp
docker compose -f mcp-servers/mcp-gateway/compose.yaml logs --tail=100 gateway
```

Add `-f` after `logs` to follow output; press Ctrl-C to stop following without stopping the container.

## Restart or rebuild one service

```bash
docker compose restart hermes
```

```bash
docker compose \
  -f mcp-servers/document-graph/compose.yaml \
  -f mcp-servers/document-graph/compose.hermes-network.yaml \
  up -d --build document-graph-mcp
```

```bash
docker compose \
  -f mcp-servers/mcp-gateway/compose.yaml \
  -f mcp-servers/mcp-gateway/compose.hermes-network.yaml \
  up -d --build gateway
```

Use both files whenever an MCP service must remain attached to Hermes.

## Stop without removing containers

This preserves the containers so they can be restarted quickly:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml stop
docker compose -f mcp-servers/document-graph/compose.yaml -f mcp-servers/document-graph/compose.hermes-network.yaml stop
docker compose stop
```

Start them again with the commands in **Start everything**.

## Stop and remove the Compose containers

Run `down` with the same file combinations used for `up`:

```bash
docker compose -f mcp-servers/mcp-gateway/compose.yaml -f mcp-servers/mcp-gateway/compose.hermes-network.yaml down
docker compose -f mcp-servers/document-graph/compose.yaml -f mcp-servers/document-graph/compose.hermes-network.yaml down
docker compose down
```

This removes containers and project-owned networks. It does not remove the external `horology_default` network, repository files, private environment files or Neon data.

After all three projects are down, remove the shared network only if you no longer need it:

```bash
docker network rm horology_default
```

Do not add `--volumes` casually. Hermes state lives in the repository's ignored `hermes-data/` bind mount; deleting that directory removes local configuration, sessions and other runtime state. MCP business data remains in Neon.

## Run an MCP service without Hermes

Use only the base file. The service gets its own private Compose network and still publishes its loopback port:

```bash
docker compose -f mcp-servers/document-graph/compose.yaml up -d --build
docker compose -f mcp-servers/mcp-gateway/compose.yaml up -d --build
```

## Troubleshooting

- **External network not found:** run `docker network create horology_default`, then repeat the `up` command.
- **Port already in use:** use `docker compose ... ps` to check whether an older project is already running. Stop that exact project before retrying.
- **Hermes cannot reach an MCP service:** recreate that service with both its base and `compose.hermes-network.yaml` files.
- **Configuration changed but behavior did not:** rebuild the relevant MCP image. For Hermes settings, use the Hermes CLI; the running process can overwrite direct edits to `hermes-data/config.yaml`.
- **A service exits immediately:** inspect its logs and confirm its own environment file exists. Do not move service credentials into the root `.env`.
