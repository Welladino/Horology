# Hermes Setup

Hermes-specific setup: the one-time provider wizard, dashboard account/login, and where personas live in the running container. For starting/stopping the whole stack (all three containers) or the general Docker layout, see [`docs/runbook/docker/running_all_services.md`](running_all_services.md).

Background/rationale for choosing Docker over the `curl | bash` installer, and Hermes over Claude Code CLI for automation, is in [`docs/planning/notes/2026-08-05_horology-founding-decisions_note.md`](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-08-05_horology-founding-decisions_note.md).

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

## Personas

The repository no longer holds the persona files (removed 2026-10-16; previous versions at `git show 55f7818:personas/...`). The running container keeps its own copies: `/opt/data/SOUL.md` (Second-Soul), `/opt/data/profiles/<name>/SOUL.md` per subagent, and the index at `/opt/data/personas/subagents/INDEX.md`. The next Hermes setup rebuilds them on the plugin structure.

To change one now, write the file locally and copy it in, for example:

```bash
docker cp SOUL.md horology-hermes:/opt/data/profiles/gtm-manager/SOUL.md
```

Verify it took effect:

```bash
docker exec horology-hermes hermes chat -q "What subagents are available to you and what's each one's scope, in one line each?"
```

### Why persona files use absolute paths (`/opt/data/...`), not relative ones

`SOUL.md`'s own instructions reference `/opt/data/personas/subagents/INDEX.md` as an absolute path deliberately, not `personas/subagents/INDEX.md`. The agent's file-tool working directory is `/opt/hermes` (Hermes's own installed codebase), not `/opt/data` (our mounted volume) — a relative path resolves against the wrong root and the agent will report the file "doesn't exist." Confirmed by testing: the first version of this instruction (relative path) failed with exactly that error; switching to the absolute `/opt/data/...` path fixed it. Any future persona/index file that references another file by path should use the full `/opt/data/...` form.

## Syncing cron scripts into the running container

Cron `--script` files (e.g. `scripts/check_unembedded_documents.py`) are authored and version-controlled in this repo under `scripts/`, then copied into the running container's `/opt/data/scripts/`. Hermes only reads scripts by relative filename from that directory (`hermes cron create ... --script <filename>`); absolute/`~` paths outside it aren't supported.

After editing a script in the repo:

```bash
docker cp scripts/check_unembedded_documents.py horology-hermes:/opt/data/scripts/check_unembedded_documents.py
```

There's no automatic sync: copy each changed script with `docker cp` (few enough scripts that a file watcher isn't worth building yet).

### Cron script runtime notes (verified hands-on, 2026-08-07)

- `.sh`/`.bash` scripts run under bash; anything else (e.g. `.py`) runs under Hermes's own bundled Python interpreter (`/opt/hermes/.venv/bin/python3` inside the container) — **not** the repo's own `.venv`. Check what's importable there before assuming a dependency is available: `docker exec horology-hermes /opt/hermes/.venv/bin/python3 -c "import <module>"`. Confirmed `psycopg2` is *not* present there but `asyncpg` is — `scripts/check_unembedded_documents.py` uses `asyncpg` for exactly this reason, unlike the MCP servers, which use Psycopg 3.
- Cron scripts do **not** inherit Hermes-managed secrets (provider API keys, etc.) — confirmed by design, per Hermes's own docs. A script needing a credential (e.g. a database connection string) needs its own env var, added to the `hermes` service's `environment:` block in `docker-compose.yml` (a plain container env var survives into the cron subprocess fine — verified hands-on; it's specifically *Hermes-managed* secrets that get stripped, not every env var).
- **The `wakeAgent` gate** (a cron job's `--script`, without `--no-agent`, decides at runtime whether the agent should run at all): a final stdout line of exactly `{"wakeAgent": false}` skips the agent entirely for that run — confirmed zero LLM turn, `hermes cron runs <job_id>` shows "Script gate returned `wakeAgent=false` — agent skipped." Any other outcome (line omitted, or `{"wakeAgent": true}`) wakes the agent and injects **all** of the script's stdout — including the gate line itself, unstripped — verbatim into the agent's prompt under a "## Script Output" heading. This is the mechanism behind the daily document-graph embedding sweep (see [`docs/planning/notes/2026-08-06_document-graph-v1_note.md`](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-08-06_document-graph-v1_note.md)) — cheap on days nothing needs backfilling, an agent turn only on days something does.
- `--no-agent` is a different mode entirely (script IS the whole job, stdout delivered verbatim, no agent involved ever) — not used for the embedding sweep, since that needs an agent to actually call `auto_link_similar_documents` when something is found.
- To test a job immediately without waiting for its schedule: `hermes cron run <job_id>`. Output lands in `/opt/data/cron/output/<job_id>/<timestamp>.md`.

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

# Copy in its persona (write SOUL.md locally first)
docker cp SOUL.md horology-hermes:/opt/data/profiles/<name>/SOUL.md

# Connect the MCP servers it needs (repeat per server, per profile)
printf "n\ny\n" | docker exec -i horology-hermes hermes -p <name> mcp add document-graph --url http://document-graph-mcp:8765/mcp

# Trim skills/tools to the minimum justified for its role
printf "y\n" | docker exec -i horology-hermes hermes -p <name> skills opt-out --remove --yes
docker exec horology-hermes hermes -p <name> tools disable computer_use image_gen video_gen video bfl vision homeassistant spotify yuanbao tts stt x_search code_execution terminal delegation cronjob browser

# Cap web searches (native guardrail — see "Web search backend" section below)
docker exec horology-hermes hermes -p <name> config set tool_loop_guardrails.loop_caps.max_web_searches 10

# Add a row to the index Second-Soul reads (edit a local copy, then copy it back)
docker cp horology-hermes:/opt/data/personas/subagents/INDEX.md INDEX.md
docker cp INDEX.md horology-hermes:/opt/data/personas/subagents/INDEX.md
```

## Web search backend (Tavily)

Hermes's built-in `web` toolset auto-detects its backend from whichever recognized API key is present, but the backend itself (`web.backend`) is a **per-profile config value**, not global — must be set on every profile that uses web search, not just the default one.

```bash
# Key goes in hermes-data/.env (Hermes's own secrets file), NOT the root .env:
echo "TAVILY_API_KEY=tvly-..." >> hermes-data/.env

# Set the backend on every profile that has the web toolset enabled
docker exec horology-hermes hermes config set web.backend tavily
docker exec horology-hermes hermes -p gtm-manager config set web.backend tavily
docker exec horology-hermes hermes -p marketing-executive config set web.backend tavily
docker exec horology-hermes hermes -p code-sentinel config set web.backend tavily

# Cap searches per turn (native guardrail, blocks cleanly with an explanation once hit)
docker exec horology-hermes hermes config set tool_loop_guardrails.loop_caps.max_web_searches 10
docker exec horology-hermes hermes -p gtm-manager config set tool_loop_guardrails.loop_caps.max_web_searches 10
docker exec horology-hermes hermes -p marketing-executive config set tool_loop_guardrails.loop_caps.max_web_searches 10
docker exec horology-hermes hermes -p code-sentinel config set tool_loop_guardrails.loop_caps.max_web_searches 10
```

Hermes has no fallback web-search backend and no crawl/map/sheets tools wired in (Tavily's basic search/extract only) — see [`docs/planning/research/2026-08-06_tavily-feature-surface-and-web-fallback_research.md`](https://github.com/Welladino/Horology/blob/main/docs/planning/research/2026-08-06_tavily-feature-surface-and-web-fallback_research.md).

Verify: `hermes doctor` should show `✓ web` with no missing-key warning; a real query (`hermes chat -q "..."`) should return actual search results.

### Troubleshooting

- **Container won't start / immediately exits:** `docker compose logs hermes` — usually a malformed `hermes-data/config.yaml` or a missing required env var (Compose will error clearly if `DASHBOARD_PASSWORD` isn't set, since it's marked required in `docker-compose.yml`).
- **Dashboard shows 302/redirect instead of a page when curl'd directly:** normal — that's the auth redirect; a browser will follow it to the login page.
- **Changed `.env` but nothing changed:** Compose only re-reads `.env` when the container is recreated, not just restarted. Use `docker compose up -d` (not `docker compose restart`) after editing `.env`.
- **Edited `config.yaml` directly on disk and the change didn't stick:** don't — the live gateway process holds its own in-memory config and can silently revert direct file edits while running. Use `hermes config set` / `hermes fallback add` / equivalent CLI commands instead.
