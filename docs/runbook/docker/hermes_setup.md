# Hermes Setup

Hermes-specific setup: the one-time provider wizard, dashboard account/login, and syncing personas from this repo into the running container. For starting/stopping the whole stack (all three containers) or the general Docker layout, see [`docs/runbook/docker/running_all_services.md`](running_all_services.md).

Background/rationale for choosing Docker over the `curl | bash` installer, and Hermes over Claude Code CLI for automation, is in [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](../../planning/notes/2026-08-05_horology-founding-decisions_note.md).

## One-time provider setup

Only needed if `hermes-data/` is empty, or you want to reconfigure the provider/model:

```bash
docker run -it --rm -v "$(pwd)/hermes-data:/opt/data" nousresearch/hermes-agent setup
```

This is a one-shot interactive wizard (`-it` for interactive input, `--rm` to delete the container afterward — it's not a long-running service). It writes `hermes-data/.env` (provider API key) and `hermes-data/config.yaml` (model choice, settings). Run `docker compose up -d` afterward to start the actual gateway with the new config.

## Dashboard account setup

The dashboard's username/password are **not** part of Hermes itself — they're basic-auth credentials Docker Compose passes in as environment variables, defined in `.env` at the repo root (separate from `hermes-data/.env`, which holds Hermes's own provider keys).

1. Copy the template if you haven't already: `cp .env.example .env`
2. Set `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` in `.env`. Generate a strong password rather than typing one, e.g.:
   ```bash
   openssl rand -hex 16
   ```
3. Set `PUID`/`PGID` to your own user's IDs (`id -u`, `id -g`) so files Hermes writes into `hermes-data/` are owned by you, not root.
4. Restart the container for changes to take effect: `docker compose up -d` (Compose recreates the container if the env changed).

`.env` is gitignored — credentials never get committed. If you ever need to rotate the dashboard password, edit `.env` and re-run `docker compose up -d`.

## Accessing the dashboard

With the container running:

- **URL:** [http://localhost:9119](http://localhost:9119)
- **Login:** the `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` from your `.env`

The dashboard gives you a browser-based chat with the running agent, plus visibility into cron jobs, skills, sessions, and logs, and a settings UI for providers/models/MCP servers — an alternative to the CLI or the native Hermes Desktop app.

The agent's OpenAI-compatible API also runs on port `8642` (no dashboard auth on that port by default — see Hermes's own docs before exposing it beyond `localhost`).

## Syncing personas into the running container

Persona files (`personas/supervisor/SOUL.md`, `personas/subagents/*.md`) are authored and version-controlled in this repo, then copied into the running container's `hermes-data/` — Hermes reads them from `/opt/data/...`, which is *not* the same as the repo copies until you sync.

After editing any persona file in the repo:

```bash
# Supervisor
docker cp personas/supervisor/SOUL.md horology-hermes:/opt/data/SOUL.md

# A subagent profile (repeat per profile that changed)
docker cp personas/subagents/gtm-manager.md horology-hermes:/opt/data/profiles/gtm-manager/SOUL.md
docker cp personas/subagents/marketing-executive.md horology-hermes:/opt/data/profiles/marketing-executive/SOUL.md
docker cp personas/subagents/code-sentinel.md horology-hermes:/opt/data/profiles/code-sentinel/SOUL.md

# The index (used by Second-Soul to decide which profile fits a task)
docker exec horology-hermes mkdir -p /opt/data/personas/subagents
docker cp personas/subagents/. horology-hermes:/opt/data/personas/subagents/
```

Verify it took effect:

```bash
docker exec horology-hermes hermes chat -q "What subagents are available to you and what's each one's scope, in one line each?"
```

There is currently no automatic sync (no file watcher) — this is a manual step after every persona edit. Worth revisiting once there are enough personas/subagents that manual `docker cp` per file becomes tedious.

### Why persona files use absolute paths (`/opt/data/...`), not relative ones

`SOUL.md`'s own instructions reference `/opt/data/personas/subagents/INDEX.md` as an absolute path deliberately, not `personas/subagents/INDEX.md`. The agent's file-tool working directory is `/opt/hermes` (Hermes's own installed codebase), not `/opt/data` (our mounted volume) — a relative path resolves against the wrong root and the agent will report the file "doesn't exist." Confirmed by testing: the first version of this instruction (relative path) failed with exactly that error; switching to the absolute `/opt/data/...` path fixed it. Any future persona/index file that references another file by path should use the full `/opt/data/...` form.

## Creating a new subagent profile

```bash
docker exec horology-hermes hermes profile create <name> --description "<one-line scope>"

# Model config goes in config.yaml, NOT profile.yaml (which only holds metadata)
docker exec horology-hermes sh -c "cat > /opt/data/profiles/<name>/config.yaml << 'EOF'
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
  base_url: https://openrouter.ai/api/v1
  api_mode: chat_completions
agent:
  max_turns: 50
EOF"
docker exec horology-hermes sh -c "grep OPENROUTER_API_KEY /opt/data/.env >> /opt/data/profiles/<name>/.env"

# Sync its persona (write personas/subagents/<name>.md in the repo first)
docker cp personas/subagents/<name>.md horology-hermes:/opt/data/profiles/<name>/SOUL.md

# Connect the MCP servers it needs (repeat per server, per profile)
printf "n\ny\n" | docker exec -i horology-hermes hermes -p <name> mcp add document-graph --url http://document-graph-mcp:8765/mcp

# Trim skills/tools to the minimum justified for its role
printf "y\n" | docker exec -i horology-hermes hermes -p <name> skills opt-out --remove --yes
docker exec horology-hermes hermes -p <name> tools disable computer_use image_gen video_gen video bfl vision homeassistant spotify yuanbao tts stt x_search code_execution terminal delegation cronjob

# Add a row to personas/subagents/INDEX.md in the repo, then sync it
docker cp personas/subagents/INDEX.md horology-hermes:/opt/data/personas/subagents/INDEX.md
```

### Troubleshooting

- **Container won't start / immediately exits:** `docker compose logs hermes` — usually a malformed `hermes-data/config.yaml` or a missing required env var (Compose will error clearly if `DASHBOARD_PASSWORD` isn't set, since it's marked required in `docker-compose.yml`).
- **Dashboard shows 302/redirect instead of a page when curl'd directly:** normal — that's the auth redirect; a browser will follow it to the login page.
- **Changed `.env` but nothing changed:** Compose only re-reads `.env` when the container is recreated, not just restarted. Use `docker compose up -d` (not `docker compose restart`) after editing `.env`.
- **Edited `config.yaml` directly on disk and the change didn't stick:** don't — the live gateway process holds its own in-memory config and can silently revert direct file edits while running. Use `hermes config set` / `hermes fallback add` / equivalent CLI commands instead.
