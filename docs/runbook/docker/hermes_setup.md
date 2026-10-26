# Hermes setup and upkeep

Hermes runs locally in Docker with three maintained roles: Coordinator for user-facing routing, Operator for trusted non-code work and Explorer for isolated Modal execution. Hermes v0.22 serves all profiles through one host-wide gateway. Its dashboard is **[http://localhost:9119](http://localhost:9119)** when the container is running; use the credentials in the root `.env`. Start and stop the three Compose projects using [Running Horology services](running_all_services.md). The current architecture is in [Hermes agents](../../architecture/hermes/hermes-agents.md).

## Install from a fresh clone

Install Git and Docker Desktop with Docker Compose v2, clone this repository,
then run from its root:

```bash
./scripts/ops/hermes/bootstrap.sh
```

The first run creates the four ignored local credential files (`.env` and the
three files below `hermes/`) from their tracked examples and stops. Fill them,
then run the command again. It builds the pinned Hermes image, creates the
profiles, applies the reviewed identities and tool configuration, installs the
Horology skills, selects Coordinator and restarts the gateway.

You do not need to clone Hermes source. Docker pulls the pinned upstream image.
OAuth logins, PATs, API keys, Modal credentials, sessions and browser cookies
are not restored from Git; authenticate them on the new machine after the
bootstrap completes. See [`hermes/README.md`](../../../hermes/README.md) for the
exact file boundaries.

## Current local setup (26 October 2026)

- `docker-compose.yml` builds `horology-hermes:v0.22.5-modal` from `ops/hermes/Dockerfile`. It pins upstream Hermes **v0.22.5** and installs the release's required optional dependency, `modal==1.5.5`.
- The protected `default` profile is presented as Coordinator. Operator handles non-code work; Explorer handles code execution in Modal.
- The reviewed profile files are tracked below `hermes/coordinator/`, `hermes/operator/` and `hermes/explorer/`. The bootstrap copies them into the live `horology-hermes-data` volume.
- Explorer uses the direct Modal backend, starts in `/root`, and has `terminal.container_persistent: false`. Its Modal and model credentials live only in its ignored `.env`; they are not forwarded into the sandbox by default.
- Hermes v0.22 uses one multiplexed root gateway for all profiles.
- The old `gtm-manager`, `marketing-executive`, `code-sentinel` and empty `turns-test` profiles, plus their persona index, were moved out of Hermes' active profile directory. The recoverable local archive is `hermes-data/archives/retired-profiles-20261023-172653/`.
- Operator connects to the HTTPS document graph and MCP gateway using OAuth. Its gateway filter selects 13 tools; `publish_synthesis` is excluded.
- Operator also has a read-only GitHub MCP connection. GitHub MCP is used for GitHub information; Git is used for repository checkout operations. The bundled GitHub skill remains disabled until a maintained replacement is selected.
- A Docker-managed volume named `horology-hermes-workspace` is mounted at `/workspace`. It currently contains the approved `Welladino/Horology` checkout and is not a bind mount to a host repository.
- Operator intentionally has no terminal or code-execution tool. Explorer owns those capabilities through Modal.
- All tracked profile configurations use SQLite `delete` journal mode.
- The old document-graph embedding-sweep cron job remains paused.

The Docker-managed `horology-hermes-data` volume holds live credentials, OAuth tokens, sessions, memories, caches and generated state. It survives container recreation but is not restored by cloning Git. Do not delete it with `docker compose down --volumes` unless you intend to erase the local Hermes installation. Reviewed identities, configuration and profile metadata are tracked under `hermes/`; the Coordinator skill is tracked under `plugins/horology-hermes/`. Rerun the bootstrap to apply them.

## Edit Operator identity and global context

The maintained identity and runtime-wide rules are deliberately separate:

- `hermes/operator/SOUL.md` contains Operator's reviewed identity, tone and general posture. `SOUL.md` is Hermes' standard identity filename; `# Operator` is the agent name.
- `hermes/operator/.hermes.md` contains stable Horology operating rules that apply across Operator tasks.
- Horology skills contain task-specific procedures, workflow fields and output requirements.

Edit the tracked files and rerun `./scripts/ops/hermes/bootstrap.sh`. Start a new Hermes session after changing identity or context so the update is loaded.

## Refresh Horology skills after a plugin update

The maintained shared skills are in `plugins/horology-workflows/skills/`, `plugins/horology-specialists/skills/`, `plugins/horology-document-graph/skills/` and `plugins/horology-tools/skills/`. The bootstrap installs them for Coordinator and Operator, except for the subscription-agent `horology-supervisor`. Coordinator's separate routing skill is `plugins/horology-hermes/skills/horology-coordinator/SKILL.md`; Operator receives neither supervisor nor coordinator.

After changing a source skill, review whether the Hermes Coordinator skill or global Operator context also needs adjustment, then rerun the bootstrap. Operator's `.hermes.md` enforces the runtime and Google-workflow boundaries globally; do not install the Claude/Codex supervisor in Hermes.

From the Horology repository root:

1. Put shared task instructions in the source plugin skill. Put Hermes-wide rules in `hermes/operator/.hermes.md`; put Hermes-only routing in `plugins/horology-hermes/skills/horology-coordinator/`.
2. Review `hermes/operator/config.yaml` if the update changes tool requirements. Do not add a tool name to the gateway filter unless the server exposes it and its policy permits it.
3. Apply the reviewed files:

   ```bash
   ./scripts/ops/hermes/bootstrap.sh
   ```

4. Check the installed skills and MCP connections:

   ```bash
   docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator skills list
   docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator mcp list
   ```

   Open a new Hermes session or run `/reload-skills` after skill edits; use `/reload-mcp` after MCP configuration edits. Confirm the changed skill appears and its reference links still resolve.

A Docker image update changes Hermes itself; rerunning the bootstrap also refreshes the project-owned skills.

## Trusted repository workspace

`/workspace` is a Docker named volume declared in `docker-compose.yml`. Docker stores it independently of the container and host checkout. Operator may inspect explicitly approved files through its file tools, but it has no local terminal or code-execution tool:

- `docker compose down` and container recreation preserve it.
- `docker compose down --volumes` or deleting `horology-hermes-workspace` deletes it.
- It is for repositories the user explicitly chooses to trust in the Hermes container. The initial allowlist contains only `Welladino/Horology`.
- Unknown repositories, forks, pull requests, new dependencies and unfamiliar build or installation scripts belong in Explorer's isolated Modal environment, not this volume.

Check the workspace and clean remote URL with:

```bash
docker exec horology-hermes ls -la /workspace
docker exec --user hermes horology-hermes git -C /workspace/Horology remote get-url origin
docker exec --user hermes horology-hermes git -C /workspace/Horology status --short
```

## MCP connections and workflow limits

Operator's document graph and gateway connections use their deployed HTTPS MCP endpoints with interactive OAuth. Their server policies determine the actual workspace, tools and budgets. Operator also has the read-only GitHub MCP configured with a fine-grained PAT from its ignored `.env`.

These connections let Hermes inspect graph history and use permitted gateway tools. The separately configured GitHub MCP supplies read-only GitHub information, while Git supplies clone, fetch and pull access to approved repositories in `/workspace`; neither supplies GitHub write access. Hermes still has no live Google Sheets/Drive editing route. Until Google access and a Hermes Pipeline execution route are configured and tested, Hermes must not claim a Pipeline run, move Stage 0–4, record a founder decision or say it saved a Drive deliverable. The Horology skill copies make that boundary explicit. A graph agent document is separate from the Sheet's Document Index.

The dashboard can add or test MCP connections and guide interactive OAuth sign-in; use it for that part if preferred. File-based skill review and merging are easier in the repository. See [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/) for connection behavior.

## Provider and dashboard setup

Use `./scripts/ops/hermes/bootstrap.sh` for both first installation and reviewed configuration updates. Root `.env` is for Docker Compose. The ignored profile files under `hermes/` hold model, Modal and connector credentials and are copied into the Docker data volume without entering Git.

With Hermes running, the dashboard is at [http://localhost:9119](http://localhost:9119). Its login comes from root `.env`. The OpenAI-compatible API is at localhost port `8642` and has no dashboard basic auth; keep it bound to localhost. Recreate the container with `docker compose up -d` after changing root `.env`.

## Update Hermes safely

Hermes is pinned through `ops/hermes/Dockerfile`; do not change the Compose image back to floating `latest`. Before changing `HERMES_VERSION` or the pinned Modal dependency:

1. Read the upstream release notes and confirm the Modal extra required by that release.
2. Stop Hermes and back up both the `horology-hermes-data` and `horology-hermes-workspace` named volumes. A Git clone restores reviewed configuration, not runtime state or credentials.
3. Build and inspect the replacement image before recreating the service:

   ```bash
   docker compose build --no-cache hermes
   docker run --rm --entrypoint /opt/hermes/.venv/bin/hermes horology-hermes:v0.22.5-modal --version
   ```

4. Recreate Hermes, inspect `docker compose logs hermes`, and verify Operator, Explorer, the trusted checkout and a disposable Modal command.
5. Keep `database.journal_mode: delete` in each tracked profile configuration unless a later Hermes migration explicitly requires otherwise.

Hermes v0.22 uses a single multiplexed host gateway. Do not restore the old per-profile gateway command; Compose must run `hermes gateway run`.

## Cron scripts

Cron `--script` files are maintained under repository `scripts/`, then copied to `/opt/data/scripts/` in the container. The bootstrap does not install cron scripts. After changing one:

```bash
docker cp scripts/check_unembedded_documents.py horology-hermes:/opt/data/scripts/check_unembedded_documents.py
```

The document-graph sweep job is **paused**. Do not resume it just because Hermes or its image was updated. Scripts run under Hermes' bundled Python or Bash, not the repository virtual environment. Cron scripts do not inherit Hermes-managed provider secrets; any required plain container environment variable must be set in Compose. A script's final `{"wakeAgent": false}` stdout line skips the agent turn for that run; `--no-agent` makes the script itself the entire job.

## Troubleshooting

- Container exits: `docker compose logs hermes`; check the tracked profile configuration and required root `.env` settings.
- Skill missing: rerun the bootstrap, then run `docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator skills list` and start a new session.
- MCP tools missing: run `docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator mcp list`, check `tools.include` in `hermes/operator/config.yaml`, and use `/reload-mcp` or start a new session.
- Operator terminal unavailable: this is intentional. Route code execution to Explorer instead of enabling local terminal access.
- Modal terminal unavailable: confirm Explorer resolves `terminal.backend: modal`, `terminal.cwd: /root` and `terminal.container_persistent: false`; then verify the image contains the exact Modal version pinned by the active Hermes release.
- When editing reviewed configuration, edit the tracked files and rerun the bootstrap. Avoid treating files inside the Docker volume as the maintained source.
