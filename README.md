# Horology

A solo founder's personal "AI co-founder" system: **Second-Soul**, a supervisor agent, dispatches recurring business work (GTM strategy, marketing content, codebase/security monitoring, and more over time) to named specialist subagents. You talk only to Second-Soul — it decides which subagent handles what.

Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research) as the runtime, with subagents as Hermes *profiles* dispatched via kanban tasks, and purpose-built MCP servers (no arbitrary API/SQL access) for anything external.

## Start here

Read in this order:

1. **[`docs/architecture/system_overview.md`](docs/architecture/system_overview.md)** — how the system actually works: the three containers, the subagent roster, the document graph, dispatch mechanism, tool caps. This is the one doc to read before touching anything.
2. **[`CLAUDE.md`](CLAUDE.md)** — how this repo's *own documentation* is organized (research vs. notes vs. architecture vs. runbook), and the conventions subagents follow when writing business documents.
3. **[`docs/planning/README.md`](docs/planning/README.md)** — the planning-doc workflow, if you're going to make a design decision and want to know where to write it up.

## Getting it running locally

You'll need your own credentials — nothing here is shared. Real secrets never leave `.env` (gitignored) and are never committed; `.env.example` is the template.

```bash
git clone https://github.com/Welladino/Horology.git && cd Horology
cp .env.example .env
```

Fill in `.env`: dashboard login, `PUID`/`PGID` (`id -u` / `id -g`), your own Neon Postgres connection strings, your own GitHub fine-grained PAT (read-only, scoped to one repo), your own OpenRouter key. Each field in `.env.example` explains where it comes from and why it's separate from the others — read the comments, they matter (e.g. provider/model keys go through `hermes-data/.env`, *not* the root `.env`).

One-time provider setup (only if `hermes-data/` is empty):

```bash
docker run -it --rm -v "$(pwd)/hermes-data:/opt/data" nousresearch/hermes-agent setup
```

Then bring up the stack:

```bash
docker compose up -d
docker compose ps
```

Dashboard: [http://localhost:9119](http://localhost:9119) (login = your `DASHBOARD_USERNAME`/`DASHBOARD_PASSWORD`).

Full setup detail (persona syncing, cron scripts, troubleshooting): [`docs/runbook/docker/hermes_setup.md`](docs/runbook/docker/hermes_setup.md) and [`docs/runbook/docker/running_all_services.md`](docs/runbook/docker/running_all_services.md).

**Before running Docker commands, keep this repo out of any folder your terminal/editor doesn't already trust with real files** — macOS gates read access to `~/Documents`, `~/Desktop`, etc. per-application, and `docker compose` inherits whichever app's terminal you run it from.

## Finding your way around the code

| Path | What's there |
|---|---|
| `personas/` | Source-of-truth persona files (`supervisor/SOUL.md`, `subagents/*.md`) — edited here, then synced into the running container. Never edit `hermes-data/` directly. |
| `mcp-servers/` | The two purpose-built MCP servers (`document-graph`, `github-monitor`) — each its own Dockerfile, `requirements.txt`, and credential. |
| `alembic/` | Postgres migrations for the document graph (Neon). Workflow: [`docs/runbook/db/alembic_workflow.md`](docs/runbook/db/alembic_workflow.md). |
| `scripts/` | Cron `--script` files, synced into the container the same way as personas. |
| `tests/` | `tests/mcp_servers/` (mocked, no Docker) and `tests/test_docker_stack.py` (real Compose stack, auto-skips if Docker isn't up). Run before shipping any change to an MCP server or `docker-compose.yml`: `python3 -m pytest tests/ -v`. See [`docs/runbook/testing/running_tests_and_audits.md`](docs/runbook/testing/running_tests_and_audits.md). |
| `docs/architecture/` | Standing reference, current state, no history — start here (see above). |
| `docs/planning/notes/` & `docs/planning/research/` | Dated trail of *why* the system looks the way it does — check here before assuming something is arbitrary. |
| `docs/runbook/` | Copy-paste-ready commands for everything operational. |

## A few things that aren't obvious from the code

- **Hermes reverts direct edits to `hermes-data/config.yaml` while it's running** — use `hermes config set` (or equivalent CLI) instead of hand-editing the file on disk.
- **The two MCP servers are not reachable from the host** — only from `hermes`, over the internal Compose network, by service name. This is deliberate (see `docs/runbook/mcp/`).
- **Documentation (including Hermes's own) has been wrong before** — if a design decision depends on how something actually behaves, verify it hands-on rather than trusting the docs.
