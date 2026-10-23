# Hermes setup and upkeep

Hermes runs locally in Docker as one default agent, Second-Soul. Its dashboard is **[http://localhost:9119](http://localhost:9119)** when the container is running; use the credentials in the root `.env`. Start and stop the three Compose projects using [Running Horology services](running_all_services.md). The current architecture is in [Hermes agents](../../architecture/hermes/hermes-agents.md).

## Current local setup (23 October 2026)

- The `horology-hermes` container uses `nousresearch/hermes-agent:latest`; the installed image tested here reported **v0.20.0**. Updating the image is a separate, intentional step.
- The default profile has 16 Horology skills: seven specialists, seven workflows, the document-graph skill and the restricted-gateway skill. Its persona is `hermes-data/SOUL.md`.
- The old `gtm-manager`, `marketing-executive`, `code-sentinel` and empty `turns-test` profiles, plus their persona index, were moved out of Hermes' active profile directory. The recoverable local archive is `hermes-data/archives/retired-profiles-20261023-172653/`.
- The default profile's `hermes-data/config.yaml` connects to the local document graph and MCP gateway. On 23 October, `hermes mcp test` discovered 19 graph tools and 14 gateway tools; the gateway filter selects 13. `publish_synthesis` is not selected for Hermes.
- The old document-graph embedding-sweep cron job remains paused. The three containers were returned to their stopped state after verification.

`hermes-data/`, including **skills, persona, MCP settings, credentials, sessions and the archive, is Git-ignored and exists only on this laptop**. A Git pull, plugin update or Docker image update does **not** refresh its Horology skill copies. The bind mount in `docker-compose.yml` preserves them when the container is recreated, but deleting `hermes-data/` would remove them. Do not put its credentials or archived profiles in Git.

## Refresh Horology skills after a plugin update

The maintained source skills are in `plugins/horology-workflows/skills/`, `plugins/horology-specialists/skills/`, `plugins/horology-document-graph/skills/` and `plugins/horology-tools/skills/`. Hermes reads local copies from `hermes-data/skills/horology-workflows/`, `horology-specialists/` and `horology-tools/` (mounted at `/opt/data/skills/` in the container).

**Whenever those plugin skills change, review and merge the changes into the Hermes copies. There is no automatic sync.** In particular, the Hermes `horology-supervisor` is deliberately rewritten for the single-agent setup; do not replace it wholesale with the Codex/Claude supervisor. Every copied workflow and specialist skill has a Hermes runtime-boundary paragraph. The graph and gateway copies also explain local workspace and bearer-token behavior. Preserve those adaptations when merging.

From the Horology repository root:

1. Compare the changed source skill with its Hermes copy. For example:

   ```bash
   diff -u plugins/horology-specialists/skills/horology-research/SKILL.md hermes-data/skills/horology-specialists/horology-research/SKILL.md
   ```

2. Merge relevant new instructions into the Hermes `SKILL.md`, keeping the Hermes runtime boundary. Copy changed reference files or assets from the source skill's directory as needed. For a new Horology skill, copy its whole directory into the matching `hermes-data/skills/horology-*/` category, then add the runtime boundary where its steps require tools Hermes does not have.
3. Review `hermes-data/SOUL.md` and `hermes-data/config.yaml` if the update changes the workflow or tool requirements. Do not add a tool name to the gateway filter unless the server exposes it and its policy permits it.
4. With Hermes running, check the installed skills and the two MCP connections:

   ```bash
   docker exec horology-hermes hermes skills list
   docker exec horology-hermes hermes mcp test document-graph
   docker exec horology-hermes hermes mcp test mcp-gateway
   ```

   Open a new Hermes session or run `/reload-skills` after skill edits; use `/reload-mcp` after MCP configuration edits. Confirm the changed skill appears and its reference links still resolve.

A Docker image update changes Hermes itself, not these copied Horology skills. If the source plugins gain a new version, repeat this checklist even when Docker is already current.

## Google Drive read-only connection

The local Hermes Google Workspace skill copy has been adapted to request **only `drive.readonly`** and to expose only Drive search, metadata and download through its wrapper. Its OAuth files are written with owner-only permissions. This is a local, Git-ignored adaptation under `hermes-data/skills/productivity/google-workspace/`; **it has no Google grant until the founder completes OAuth**. Do not run the unmodified bundled skill's default setup: it requests Gmail, Calendar, full Drive, Sheets and Docs scopes together. Review this local adaptation after any Hermes image or skill refresh.

Choose the account before granting access. `drive.readonly` covers every Drive file visible to that account. To confine the effective data set to Horology, use a separate Google account with only the Horology folders shared to it. A skill instruction or folder-name filter cannot enforce that boundary. This read-only grant does not provide Sheets/Docs editing and therefore does not yet authorize Hermes to complete Pipeline stages.

1. In a Google Cloud project controlled by the account owner, enable **Google Drive API**, create a dedicated OAuth **Desktop app** client, and include the selected account in the app's audience (or test-user list if Testing). Download the client JSON; do not paste its contents into a chat.
2. Put that file at `hermes-data/google_client_secret.json` on the Docker host and run `chmod 600 hermes-data/google_client_secret.json`. The file is mounted at `/opt/data/google_client_secret.json` and excluded from Git.
3. Run the following in a local terminal. Open the printed authorization URL yourself and confirm that the consent requests Drive read-only access only. The redirected URL contains a short-lived code; pass it via terminal input rather than a chat message or shell argument.

   ```bash
   docker exec horology-hermes python /opt/data/skills/productivity/google-workspace/scripts/setup.py --auth-url
   docker exec -i horology-hermes python /opt/data/skills/productivity/google-workspace/scripts/setup.py --auth-code -
   docker exec horology-hermes python /opt/data/skills/productivity/google-workspace/scripts/setup.py --check-live
   ```

4. Test one bounded Drive search, then reload skills or start a new Hermes session. To remove access, run `docker exec horology-hermes python /opt/data/skills/productivity/google-workspace/scripts/setup.py --revoke` and remove the local client JSON after Google confirms revocation.

If the selected account changes, revoke the previous token and authorize again. The official Google Drive MCP is another future option, but it currently requires [Google Workspace Developer Preview enrollment](https://developers.google.com/workspace/preview) and a separately registered agent OAuth client.

## MCP connections and workflow limits

The local document graph is `http://document-graph-mcp:8765/mcp` on the private `horology_default` network. It has no application sign-in in local mode and is fixed to workspace `welladino`. Keep its host port bound to `127.0.0.1`. The gateway is `http://horology-mcp-gateway:8767/mcp` on the same network and uses a bearer credential from `hermes-data/.env`; the server's client record and shared policy determine the actual tools and budgets.

These connections let Hermes inspect graph history and use permitted gateway tools. They do **not** give it live Google Sheets/Drive editing or native GitHub access. The old GitHub gateway tools were retired. Until Google access and a Hermes Pipeline execution route are configured and tested, Hermes must not claim a Pipeline run, move Stage 0–4, record a founder decision or say it saved a Drive deliverable. The Horology skill copies make that boundary explicit. A graph agent document is separate from the Sheet's Document Index.

The dashboard can add or test MCP connections and guide interactive OAuth sign-in; use it for that part if preferred. File-based skill review and merging are easier in the repository. See [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/) for connection behavior.

## Provider and dashboard setup

Only if `hermes-data/` is empty, or to reconfigure the model/provider, run the one-shot wizard from the repository root:

```bash
docker run -it --rm -v "$(pwd)/hermes-data:/opt/data" nousresearch/hermes-agent setup
```

The wizard writes `hermes-data/.env` (Hermes secrets) and `hermes-data/config.yaml`. Root `.env` is separate: Docker Compose reads its `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `PUID`, `PGID` and other service settings. To set it up, copy `.env.example` to `.env`, fill the required values, then run `docker compose up -d`.

With Hermes running, the dashboard is at [http://localhost:9119](http://localhost:9119). Its login comes from root `.env`. The OpenAI-compatible API is at localhost port `8642` and has no dashboard basic auth; keep it bound to localhost. Recreate the container with `docker compose up -d` after changing root `.env`.

## Cron scripts

Cron `--script` files are maintained under repository `scripts/`, then copied to `hermes-data/scripts/` (`/opt/data/scripts/` in the container). There is no automatic sync. After changing one:

```bash
docker cp scripts/check_unembedded_documents.py horology-hermes:/opt/data/scripts/check_unembedded_documents.py
```

The document-graph sweep job is **paused**. Do not resume it just because Hermes or its image was updated. Scripts run under Hermes' bundled Python or Bash, not the repository virtual environment. Cron scripts do not inherit Hermes-managed provider secrets; any required plain container environment variable must be set in Compose. A script's final `{"wakeAgent": false}` stdout line skips the agent turn for that run; `--no-agent` makes the script itself the entire job.

## Troubleshooting

- Container exits: `docker compose logs hermes`; check `hermes-data/config.yaml` and required root `.env` settings.
- Skill missing: check its directory under `hermes-data/skills/`, run `docker exec horology-hermes hermes skills list`, then `/reload-skills` or start a new session.
- MCP tools missing: run the two `hermes mcp test` commands above, check `tools.include` in `hermes-data/config.yaml`, and use `/reload-mcp` or start a new session. Discovery shows what the server offers; the filter determines what Hermes receives.
- When editing `config.yaml`, stop Hermes first or use its config UI/CLI. A running gateway can overwrite direct file edits from its in-memory settings.
