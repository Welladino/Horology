# Docker Setup Runbook

How Horology's Hermes Agent instance is run locally: starting the container, one-time account setup, and accessing the dashboard.

Background/rationale for this approach (Docker over the `curl | bash` installer, Hermes over Claude Code CLI for automation, etc.) is in [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](../../planning/notes/2026-08-05_horology-founding-decisions_note.md). This doc is the practical how-to only.

## a. Running the Docker image

Everything lives in `docker-compose.yml` at the repo root. Day-to-day commands, run from the repo root:

```bash
# Start the gateway (detached, auto-restarts on crash or reboot)
docker compose up -d

# Check it's running
docker compose ps

# Follow logs
docker compose logs -f hermes

# Stop it
docker compose down
```

All persistent state (config, API keys, sessions, memories, skills, cron jobs) lives in `hermes-data/` at the repo root, bind-mounted into the container at `/opt/data`. This folder is gitignored — it's local machine state, not something to commit. Stopping/removing the container never loses this data; only deleting `hermes-data/` itself would.

### Re-running first-time setup (only if `hermes-data/` is empty or you want to reconfigure the provider/model)

```bash
docker run -it --rm -v "$(pwd)/hermes-data:/opt/data" nousresearch/hermes-agent setup
```

This is a one-shot interactive wizard (`-it` for interactive input, `--rm` to delete the container afterward — it's not a long-running service). It writes `hermes-data/.env` (provider API key) and `hermes-data/config.yaml` (model choice, settings). Run `docker compose up -d` afterward to start the actual gateway with the new config.

## b. Local account (dashboard login) setup

The dashboard's username/password are **not** part of Hermes itself — they're basic-auth credentials Docker Compose passes in as environment variables, defined in `.env` at the repo root (separate from `hermes-data/.env`, which holds Hermes's own provider keys — see the founding-decisions note for why these are two different files).

1. Copy the template if you haven't already: `cp .env.example .env`
2. Set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in `.env`. Generate a strong password rather than typing one, e.g.:
   ```bash
   openssl rand -hex 16
   ```
3. Set `PUID`/`PGID` to your own user's IDs (`id -u`, `id -g`) so files Hermes writes into `hermes-data/` are owned by you, not root.
4. Restart the container for changes to take effect: `docker compose up -d` (Compose recreates the container if the env changed).

`.env` is gitignored — credentials never get committed. If you ever need to rotate the dashboard password, edit `.env` and re-run `docker compose up -d`.

## c. Accessing the local dashboard

With the container running:

- **URL:** [http://localhost:9119](http://localhost:9119)
- **Login:** the `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` from your `.env`

The dashboard gives you a browser-based chat with the running agent, plus visibility into cron jobs, skills, sessions, and logs, and a settings UI for providers/models/MCP servers — an alternative to the CLI or the native Hermes Desktop app.

The agent's OpenAI-compatible API also runs on port `8642` (no dashboard auth on that port by default — see Hermes's own docs before exposing it beyond `localhost`).

## Syncing personas into the running container

Persona files (e.g. `personas/supervisor/SOUL.md`) are authored and version-controlled in this repo, then copied into the running container's `hermes-data/` — Hermes reads `SOUL.md` from `/opt/data/SOUL.md`, which is *not* the same as the repo's `personas/supervisor/SOUL.md` until you sync it.

After editing a persona file in the repo:

```bash
docker cp personas/supervisor/SOUL.md horology-hermes:/opt/data/SOUL.md
```

Verify it took effect:

```bash
docker exec horology-hermes hermes chat -q "In one sentence, who are you and what's your role?"
```

There is currently no automatic sync (no file watcher) — this is a manual step after every persona edit. Worth revisiting once there are enough personas/subagents that manual `docker cp` per file becomes tedious.

### Troubleshooting

- **Container won't start / immediately exits:** `docker compose logs hermes` — usually a malformed `hermes-data/config.yaml` or a missing required env var (Compose will error clearly if `DASHBOARD_PASSWORD` isn't set, since it's marked required in `docker-compose.yml`).
- **Dashboard shows 302/redirect instead of a page when curl'd directly:** normal — that's the auth redirect; a browser will follow it to the login page.
- **Changed `.env` but nothing changed:** Compose only re-reads `.env` when the container is recreated, not just restarted. Use `docker compose up -d` (not `docker compose restart`) after editing `.env`.
