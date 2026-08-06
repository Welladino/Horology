# Running Horology's Docker Services

Horology is three containers, all defined in `docker-compose.yml` at the repo root:

| Service | Container name | What it is | Reachable from host? |
|---|---|---|---|
| `hermes` | `horology-hermes` | The agent runtime itself — Second-Soul + all subagent profiles | Yes: `127.0.0.1:8642` (API, usually unused), `127.0.0.1:9119` (dashboard) |
| `document-graph-mcp` | `horology-document-graph-mcp` | MCP server: document graph (Neon) tools | No — internal Docker network only |
| `github-monitor-mcp` | `horology-github-monitor-mcp` | MCP server: read-only GitHub monitoring tools | No — internal Docker network only |

The two MCP servers are deliberately **not** reachable from your host machine — only from `hermes` itself, over the internal Compose network, by service name (`http://document-graph-mcp:8765/mcp`, `http://github-monitor-mcp:8766/mcp`). See `docs/runbook/mcp/` for what each one exposes and why they're built this way.

## Starting and stopping everything

```bash
# Start all three (detached, auto-restart on crash/reboot)
docker compose up -d

# Check status
docker compose ps

# Stop and remove all three (state in hermes-data/ and Neon is untouched)
docker compose down
```

## Starting/rebuilding one service at a time

Useful when only one server's code changed and you don't want to touch the others:

```bash
# Rebuild after editing a server's source (server.py, requirements.txt, Dockerfile)
docker compose build document-graph-mcp
docker compose build github-monitor-mcp

# Bring just that one up after rebuilding
docker compose up -d document-graph-mcp
docker compose up -d github-monitor-mcp

# hermes has no build step (uses the published nousresearch/hermes-agent image) - just recreate it
docker compose up -d hermes
```

## Logs

```bash
docker compose logs -f hermes
docker compose logs -f document-graph-mcp
docker compose logs -f github-monitor-mcp
```

## What's gitignored vs. what persists where

- **`hermes-data/`** (repo root, gitignored) — all of Hermes's own state: config, API keys, sessions, memories, skills, cron jobs, kanban tasks, every profile's own subfolder. Bind-mounted into the `hermes` container at `/opt/data`. Surviving `docker compose down`/`up` — only deleting this folder loses it.
- **The two MCP servers hold no persistent state of their own** — `document-graph-mcp` reads/writes Neon (external, not in this repo); `github-monitor-mcp` only calls the GitHub API. Nothing to lose by recreating either container.
- **`.env`** (repo root, gitignored) — dashboard credentials, `PUID`/`PGID`, and the credentials each MCP server's container environment needs (`DATABASE_URL_POOLED`, `GITHUB_TOKEN`, `GITHUB_REPO`). See `.env.example` for the full list with explanations.

## For Hermes-specific setup (first-time wizard, dashboard login, persona syncing)

See [`docs/runbook/docker/hermes_setup.md`](hermes_setup.md).

## For what each MCP server does and how to test/connect it

See [`docs/runbook/mcp/`](../mcp/).
