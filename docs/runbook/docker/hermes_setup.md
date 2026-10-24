# Hermes setup and upkeep

Hermes runs locally in Docker with two maintained profiles: Operator for trusted Horology work and Explorer for isolated Modal execution. Hermes v0.22 serves both through one host-wide gateway. Its dashboard is **[http://localhost:9119](http://localhost:9119)** when the container is running; use the credentials in the root `.env`. Start and stop the three Compose projects using [Running Horology services](running_all_services.md). The current architecture is in [Hermes agents](../../architecture/hermes/hermes-agents.md).

## Current local setup (24 October 2026)

- `docker-compose.yml` builds `horology-hermes:v0.22.5-modal` from `ops/hermes/Dockerfile`. It pins upstream Hermes **v0.22.5** and installs the release's required optional dependency, `modal==1.5.5`.
- Operator has the maintained Horology skills, trusted repository workspace, MCP connections and provider credentials. Its identity is defined in Hermes' standard `hermes-data/profiles/operator/SOUL.md` file.
- Explorer uses the direct Modal backend, starts in `/root`, and has `terminal.container_persistent: false`. Its Modal and model credentials live only in `hermes-data/profiles/explorer/.env`; they are not forwarded into the sandbox.
- Hermes v0.22 uses one multiplexed root gateway for all profiles. The protected `default` profile remains as Hermes' host root; select Operator for normal work and Explorer only for isolated work.
- The old `gtm-manager`, `marketing-executive`, `code-sentinel` and empty `turns-test` profiles, plus their persona index, were moved out of Hermes' active profile directory. The recoverable local archive is `hermes-data/archives/retired-profiles-20261023-172653/`.
- Operator's `hermes-data/profiles/operator/config.yaml` connects to the local document graph and MCP gateway. On 23 October, `hermes mcp test` discovered 19 graph tools and 14 gateway tools; the gateway filter selects 13. `publish_synthesis` is not selected for Hermes.
- Operator also has a read-only GitHub MCP connection. GitHub MCP is used for GitHub information; Git is used for repository checkout operations. The bundled GitHub skill remains disabled until a maintained replacement is selected.
- A Docker-managed volume named `horology-hermes-workspace` is mounted at `/workspace`. It currently contains the approved `Welladino/Horology` checkout and is not a bind mount to a host repository.
- Operator's CLI toolsets include `terminal` and `code_execution`. Terminal commands start in `/workspace`; repository-specific commands must change to the selected checkout, such as `/workspace/Horology`.
- All live Hermes `state.db` files use SQLite `delete` journal mode because `hermes-data/` is a macOS bind mount; WAL mode is unsafe across Docker Desktop's VM filesystem boundary.
- The old document-graph embedding-sweep cron job remains paused.

`hermes-data/`, including **identity, context, skills, MCP settings, credentials, sessions and the archive, is Git-ignored and exists only on this laptop**. A Git pull, plugin update or Docker image update does **not** refresh its adapted skill copies automatically. The bind mount in `docker-compose.yml` preserves the directory when the container is recreated, but deleting `hermes-data/` would remove this local state. Do not put its credentials or archived profiles in Git.

## Edit Operator identity and global context

The maintained identity and runtime-wide rules are deliberately separate:

- `hermes-data/profiles/operator/SOUL.md` contains Operator's identity, tone and general posture. `SOUL.md` is Hermes' standard identity filename; `# Operator` is the agent name.
- `hermes-data/profiles/operator/.hermes.md` contains stable Horology operating rules that apply across Operator tasks.
- Horology skills contain task-specific procedures, workflow fields and output requirements.

Edit these local files directly or use the dashboard's **Edit SOUL** control for the identity. Start a new Hermes session after changing either file so the updated identity and project context are loaded.

## Refresh Horology skills after a plugin update

The maintained source skills are in `plugins/horology-workflows/skills/`, `plugins/horology-specialists/skills/`, `plugins/horology-document-graph/skills/` and `plugins/horology-tools/skills/`. Operator reads local copies below `hermes-data/profiles/operator/skills/` (mounted below `/opt/data/profiles/operator/skills/` in the container).

**Whenever those plugin skills change, review and merge the changes into the Hermes copies. There is no automatic sync.** In particular, the Hermes `horology-supervisor` is deliberately rewritten for the single-agent setup; do not replace it wholesale with the Codex/Claude supervisor. Every copied workflow and specialist skill has a Hermes runtime-boundary paragraph. The graph and gateway copies also explain local workspace and bearer-token behavior. Preserve those adaptations when merging.

From the Horology repository root:

1. Compare the changed source skill with its Hermes copy. For example:

   ```bash
   diff -u plugins/horology-specialists/skills/horology-research/SKILL.md hermes-data/profiles/operator/skills/horology-specialists/horology-research/SKILL.md
   ```

2. Merge relevant new instructions into the Hermes `SKILL.md`, keeping the Hermes runtime boundary. Copy changed reference files or assets from the source skill's directory as needed. For a new Horology skill, copy its whole directory into the matching `hermes-data/profiles/operator/skills/horology-*/` category, then add the runtime boundary where its steps require tools Hermes does not have.
3. Put agent-wide rules in `hermes-data/profiles/operator/.hermes.md`. Put task-specific rules in the relevant maintained skill and merge them into its Hermes copy. Review `hermes-data/profiles/operator/config.yaml` if the update changes tool requirements. Do not add a tool name to the gateway filter unless the server exposes it and its policy permits it.
4. With Hermes running, check the installed skills and the two MCP connections:

   ```bash
   docker exec horology-hermes hermes -p operator skills list
   docker exec horology-hermes hermes -p operator mcp test document-graph
   docker exec horology-hermes hermes -p operator mcp test mcp-gateway
   ```

   Open a new Hermes session or run `/reload-skills` after skill edits; use `/reload-mcp` after MCP configuration edits. Confirm the changed skill appears and its reference links still resolve.

A Docker image update changes Hermes itself, not these copied Horology skills. If the source plugins gain a new version, repeat this checklist even when Docker is already current.

## Trusted repository workspace

Operator starts terminal work in `/workspace`, a Docker named volume declared in `docker-compose.yml`. Docker stores it independently of the container and host checkout:

- `docker compose down` and container recreation preserve it.
- `docker compose down --volumes` or deleting `horology-hermes-workspace` deletes it.
- It is for repositories the user explicitly chooses to trust in the Hermes container. The initial allowlist contains only `Welladino/Horology`.
- Unknown repositories, forks, pull requests, new dependencies and unfamiliar build or installation scripts belong in the future isolated Explorer environment, not this volume.

The ignored `/opt/data/.gitconfig` points GitHub HTTPS authentication to `/opt/data/bin/git-credential-hermes-github`. That helper reads `GITHUB_TOKEN`, falling back to the existing `GITHUB_MCP_TOKEN`, without storing the token in Git configuration, a credential store or the repository remote. The fine-grained token remains restricted to its selected repositories and read-only Contents permission.

Check the workspace and clean remote URL with:

```bash
docker exec horology-hermes ls -la /workspace
docker exec --user hermes horology-hermes git -C /workspace/Horology remote get-url origin
docker exec --user hermes horology-hermes git -C /workspace/Horology status --short
```

The removed bundled GitHub and Google Workspace skills must not be restored accidentally during a skill refresh. Maintained replacements will be linked to Operator later.

## MCP connections and workflow limits

The local document graph is `http://document-graph-mcp:8765/mcp` on the private `horology_default` network. It has no application sign-in in local mode and is fixed to workspace `welladino`. Keep its host port bound to `127.0.0.1`. The gateway is `http://horology-mcp-gateway:8767/mcp` on the same network and uses a bearer credential from `hermes-data/.env`; the server's client record and shared policy determine the actual tools and budgets.

These connections let Hermes inspect graph history and use permitted gateway tools. The separately configured GitHub MCP supplies read-only GitHub information, while Git supplies clone, fetch and pull access to approved repositories in `/workspace`; neither supplies GitHub write access. Hermes still has no live Google Sheets/Drive editing route. Until Google access and a Hermes Pipeline execution route are configured and tested, Hermes must not claim a Pipeline run, move Stage 0–4, record a founder decision or say it saved a Drive deliverable. The Horology skill copies make that boundary explicit. A graph agent document is separate from the Sheet's Document Index.

The dashboard can add or test MCP connections and guide interactive OAuth sign-in; use it for that part if preferred. File-based skill review and merging are easier in the repository. See [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/) for connection behavior.

## Provider and dashboard setup

Only if `hermes-data/` is empty, or to reconfigure the model/provider, run the one-shot wizard from the repository root:

```bash
docker run -it --rm -v "$(pwd)/hermes-data:/opt/data" nousresearch/hermes-agent setup
```

The wizard writes `hermes-data/.env` (Hermes secrets) and `hermes-data/config.yaml`. Root `.env` is separate: Docker Compose reads its `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `PUID`, `PGID` and other service settings. To set it up, copy `.env.example` to `.env`, fill the required values, then run `docker compose up -d`.

With Hermes running, the dashboard is at [http://localhost:9119](http://localhost:9119). Its login comes from root `.env`. The OpenAI-compatible API is at localhost port `8642` and has no dashboard basic auth; keep it bound to localhost. Recreate the container with `docker compose up -d` after changing root `.env`.

## Update Hermes safely

Hermes is pinned through `ops/hermes/Dockerfile`; do not change the Compose image back to floating `latest`. Before changing `HERMES_VERSION` or the pinned Modal dependency:

1. Read the upstream release notes and confirm the Modal extra required by that release.
2. Stop Hermes and back up both `hermes-data/` and the `horology-hermes-workspace` named volume. Local pre-v0.22.5 rollback archives are under the Git-ignored `hermes-data/backups/pre-v0.22.5-2026-10-24/` directory.
3. Build and inspect the replacement image before recreating the service:

   ```bash
   docker compose build --no-cache hermes
   docker run --rm --entrypoint /opt/hermes/.venv/bin/hermes horology-hermes:v0.22.5-modal --version
   ```

4. Recreate Hermes, inspect `docker compose logs hermes`, and verify Operator, Explorer, the trusted checkout and a disposable Modal command.
5. If Hermes reports a WAL database on the macOS bind mount, stop every Hermes process and use `hermes sessions set-journal-mode delete` for every live profile. Keep `database.journal_mode: delete` in each profile configuration.

Hermes v0.22 uses a single multiplexed host gateway. Do not restore the old per-profile gateway command; Compose must run `hermes gateway run`.

## Cron scripts

Cron `--script` files are maintained under repository `scripts/`, then copied to `hermes-data/scripts/` (`/opt/data/scripts/` in the container). There is no automatic sync. After changing one:

```bash
docker cp scripts/check_unembedded_documents.py horology-hermes:/opt/data/scripts/check_unembedded_documents.py
```

The document-graph sweep job is **paused**. Do not resume it just because Hermes or its image was updated. Scripts run under Hermes' bundled Python or Bash, not the repository virtual environment. Cron scripts do not inherit Hermes-managed provider secrets; any required plain container environment variable must be set in Compose. A script's final `{"wakeAgent": false}` stdout line skips the agent turn for that run; `--no-agent` makes the script itself the entire job.

## Troubleshooting

- Container exits: `docker compose logs hermes`; check `hermes-data/config.yaml` and required root `.env` settings.
- Skill missing: check its directory under `hermes-data/profiles/operator/skills/`, run `docker exec horology-hermes hermes -p operator skills list`, then `/reload-skills` or start a new session.
- MCP tools missing: run the two profile-specific `hermes mcp test` commands above, check `tools.include` in `hermes-data/profiles/operator/config.yaml`, and use `/reload-mcp` or start a new session. Discovery shows what the server offers; the filter determines what Hermes receives.
- Terminal unavailable: run `docker exec horology-hermes hermes tools list --platform cli`. If needed, enable it with `docker exec horology-hermes hermes tools enable --platform cli terminal code_execution`, restart Hermes and start a new session so the updated tool schema is loaded.
- Modal terminal unavailable: confirm Explorer resolves `terminal.backend: modal`, `terminal.cwd: /root` and `terminal.container_persistent: false`; then verify the image contains the exact Modal version pinned by the active Hermes release.
- When editing `config.yaml`, stop Hermes first or use its config UI/CLI. A running gateway can overwrite direct file edits from its in-memory settings.
