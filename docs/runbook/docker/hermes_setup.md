# Hermes setup and upkeep

Hermes runs locally in Docker with three maintained profiles. One host-wide
gateway serves all three.

| Profile | Purpose | Main access |
|---|---|---|
| **Coordinator** | User-facing planning, approval, routing and synthesis | Read-only Google workspace inspection and Kanban routing |
| **Operator** | Trusted non-code research, browser, document and connected-service work | Approved Google writes, document graph, restricted gateway and read-only GitHub |
| **Explorer** | Code execution, dependency experiments and unfamiliar repository work | Ephemeral Modal sandbox |

When Hermes is running:

- Dashboard: **[http://localhost:9119](http://localhost:9119)**, using the credentials in the root `.env`.
- OpenAI-compatible API: `http://localhost:8642`, bound to localhost and without dashboard basic auth.

Related documentation:

- Start and stop all local services: [Running Horology services](running_all_services.md).
- Understand the profiles and data boundaries: [Hermes agents](../../architecture/hermes/hermes-agents.md).
- Set up and use isolated code execution: [Modal sandbox for Explorer](modal_sandbox.md).
- Add or change hosted connections: [Composio MCP for Hermes](../mcp/composio.md).
- See the tracked and private file boundaries: [`hermes/README.md`](../../../hermes/README.md).

## Install on a new machine

### 1. Install the prerequisites

Install Git and Docker Desktop, which includes Docker Compose v2. Open Docker
Desktop and wait until Docker is running.

Confirm both tools in Terminal:

```bash
git --version
docker --version
docker compose version
```

The bootstrap does not install these programs and cannot run without Docker.

### 2. Clone Horology

Clone this repository and enter it:

```bash
git clone https://github.com/Welladino/Horology.git
cd Horology
```

Do not clone the upstream Hermes Git repository. Docker obtains Hermes from its
published container image instead.

### 3. Run the bootstrap once

From the Horology repository root:

```bash
./scripts/ops/hermes/bootstrap.sh
```

The first run creates the ignored local credential files and then stops:

| File | Used by |
|---|---|
| `.env` | Docker Compose and the Hermes dashboard |
| `hermes/.env` | Coordinator |
| `hermes/operator/.env` | Operator |
| `hermes/explorer/.env` | Explorer and Modal |

### 4. Add local credentials

Fill the required values in those four files. Follow
[`hermes/README.md`](../../../hermes/README.md) for which credentials belong in
each profile.

The real `.env` files are ignored by Git. Never place PATs, OAuth tokens, API
keys or passwords in tracked YAML, `.env.example` files or documentation.

### 5. Run the bootstrap again

```bash
./scripts/ops/hermes/bootstrap.sh
```

The second run builds and starts Hermes, creates Operator and Explorer if they
are missing, applies the reviewed profiles and skills, copies the ignored
credentials into the appropriate profiles, selects Coordinator and restarts
the gateway.

The script is safe to rerun. It updates reviewed files and skill contents but
does not delete sessions, memories, workspace files, OAuth tokens or other
runtime state.

### 6. Finish authentication and verify

OAuth logins, PATs, API keys, Modal credentials, sessions and browser cookies
are not restored from Git. Complete the required sign-ins on the new machine.

Then verify the local image and container:

```bash
docker image inspect horology-hermes:v0.22.5-modal
docker compose ps
```

Open [http://localhost:9119](http://localhost:9119) and confirm that
Coordinator, Operator and Explorer are available.

## Where the Hermes image comes from

Nous Research has already built Hermes and published this upstream image on
Docker Hub:

```text
nousresearch/hermes-agent:v0.22.5
```

Docker Hub is an image registry for ready-built container images. It is
separate from the Hermes Git repository. On a new machine, Docker downloads
the published image directly from Docker Hub (`docker.io`); it does not visit,
clone or build the Hermes Git repository.

The user does not need to download the image manually. The tracked
`ops/hermes/Dockerfile` begins with:

```dockerfile
FROM nousresearch/hermes-agent:v0.22.5
```

If that image is absent locally, Docker automatically performs the equivalent
of:

```bash
docker pull nousresearch/hermes-agent:v0.22.5
```

The build then installs the pinned Modal dependency and Compose names the
resulting local image `horology-hermes:v0.22.5-modal`.

| Item | What it is | Where it comes from |
|---|---|---|
| `nousresearch/hermes-agent:v0.22.5` | Ready-built upstream base image | Published by Nous Research on Docker Hub |
| `ops/hermes/Dockerfile` | Horology's tracked build recipe | This Git repository |
| `horology-hermes:v0.22.5-modal` | Locally built Hermes image with Modal | Built automatically on the user's machine |
| `horology-hermes` | Running container | Created by Docker Compose from the local image |

The customized image does not need to be published to Docker Hub. Every new
machine can rebuild it from Horology's Dockerfile and Nous Research's published
base image. There is no separate `docker pull`, `docker tag` or Hermes
source-clone step for the user.

## Current maintained configuration

Current as of **27 October 2026**.

### Runtime

- `docker-compose.yml` builds `horology-hermes:v0.22.5-modal` from
  `ops/hermes/Dockerfile`.
- Hermes is pinned to **v0.22.5** and Modal to **1.5.5**.
- Hermes v0.22 uses one multiplexed root gateway for all profiles.
- The protected `default` profile is presented as Coordinator.
- All tracked profile configurations use SQLite `delete` journal mode.
- The old document-graph embedding-sweep cron job is paused.

### Profile boundaries

- **Coordinator** has a read-only Composio session for Pipeline, Locations,
  registers, Drive and Docs.
- **Operator** has no terminal or code-execution tool. It has a separate,
  selectively write-capable Composio session for approved Google Workspace
  work.
- **Explorer** owns code execution through direct Modal. It starts in `/root`,
  uses `terminal.container_persistent: false`, and does not receive local
  workspace or profile credentials by default. Follow the
  [Modal sandbox runbook](modal_sandbox.md) for setup, verification, task input
  and artifact export.

The retired `gtm-manager`, `marketing-executive`, `code-sentinel` and empty
`turns-test` profiles, plus their persona index, were moved out of Hermes'
active profile directory. Their recoverable local archive is
`hermes-data/archives/retired-profiles-20261023-172653/`.

### Connections

| Connection | Profile | Boundary |
|---|---|---|
| Document graph and restricted gateway | Operator | Deployed HTTPS MCPs with OAuth; gateway selects 13 tools and excludes `publish_synthesis` |
| GitHub MCP | Operator | Read-only GitHub information through a fine-grained PAT |
| Git | Trusted `/workspace` checkout | Clone, fetch and pull only; it does not provide GitHub write access |
| Composio | Coordinator | Read-only Google workspace inspection |
| Composio | Operator | Approved Google Workspace reads and writes allowed by its Session Config |

The bundled GitHub skill remains disabled until a maintained replacement is
selected. Composio permissions and MCP URLs are maintained separately for
Coordinator and Operator; see the [Composio runbook](../mcp/composio.md).

### Tracked files and runtime state

| Data | Location | Restored by Git clone? |
|---|---|---:|
| Reviewed identities, profile configuration and metadata | `hermes/{coordinator,operator,explorer}/` | Yes |
| Shared and Hermes-only skill sources | `plugins/horology-*` | Yes |
| API keys and profile credentials | Ignored local `.env` files, copied into the data volume | No |
| Sessions, memories, OAuth tokens, caches and generated state | `horology-hermes-data` Docker volume at `/opt/data` | No |
| Approved repository checkouts | `horology-hermes-workspace` Docker volume at `/workspace` | No |
| User-facing generated deliverables | `hermes/hermes-output/`, mounted at `/workspace/output` | No; generated files are ignored and remain local |

The two Docker volumes survive container recreation and `docker compose down`.
Do not run `docker compose down --volumes` unless you intend to erase the local
Hermes installation and trusted workspace.

## Apply reviewed changes

Use the bootstrap for both initial installation and later reviewed
configuration updates:

```bash
./scripts/ops/hermes/bootstrap.sh
```

Edit tracked files in this repository, not generated copies inside the Docker
volume. Rerunning the bootstrap copies the maintained source into the live
profiles.

### Change identity or global context

Each profile keeps stable identity and context separate:

- `SOUL.md` contains the reviewed identity, tone and general posture. The
  filename is part of Hermes' identity system; its heading names the profile.
- `.hermes.md` contains stable Horology operating rules that apply across
  tasks.
- Skills contain task-specific procedures, workflow fields and output
  requirements.

After editing these files, rerun the bootstrap and start a new Hermes session
so the updated identity and context are loaded.

### Refresh Horology skills

Maintained shared skills live in:

- `plugins/horology-workflows/skills/`;
- `plugins/horology-specialists/skills/`;
- `plugins/horology-document-graph/skills/`;
- `plugins/horology-tools/skills/`.

The bootstrap installs them for Coordinator and Operator, except for the
subscription-agent `horology-supervisor`. Coordinator instead receives
`plugins/horology-hermes/skills/horology-coordinator`; Operator receives
neither supervisor nor coordinator. Explorer receives no workflow skills.

When changing a skill:

1. Put shared task instructions in the relevant source plugin skill.
2. Put Hermes-wide Operator rules in `hermes/operator/.hermes.md` and
   Hermes-only routing in `plugins/horology-hermes/skills/horology-coordinator/`.
3. Review `hermes/operator/config.yaml` if tool requirements change. Do not add
   a gateway tool unless the server exposes it and its policy permits it.
4. Apply the change:

   ```bash
   ./scripts/ops/hermes/bootstrap.sh
   ```

5. Verify the installed skills and MCP connections:

   ```bash
   docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator skills list
   docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator mcp list
   ```

Open a new session or run `/reload-skills` after skill edits. Use `/reload-mcp`
after MCP edits. Confirm that changed skills appear and their references still
resolve. A Docker image update changes Hermes itself; rerunning the bootstrap
also refreshes project-owned skills.

## MCP connections and workflow limits

The document graph and restricted gateway use their deployed HTTPS endpoints
with interactive OAuth. Their server policies determine the workspace, tools
and budgets. GitHub uses a fine-grained PAT from Operator's ignored `.env`.
Google Workspace uses separate hosted Composio sessions: read-only for
Coordinator and selectively write-capable for Operator.

These connections let Hermes inspect graph history, use permitted gateway
tools, read the configured Google workspace and perform explicitly approved
Google writes through Operator. They do not grant GitHub write access.

Google capabilities remain limited to the tools, auth configs and connected
accounts allowed by each Composio Session Config. Horology skills still govern
Pipeline transitions, approvals and record keeping: possessing a tool does not
authorize a stage change or user decision. A graph agent document is separate
from the Sheet's Document Index.

Before changing Google access, follow the [Composio MCP runbook](../mcp/composio.md).
The dashboard can add or test MCP connections and guide interactive OAuth
sign-in. See the [Hermes MCP documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/)
for Hermes connection behavior.

## Trusted repository workspace

`/workspace` is the Docker named volume `horology-hermes-workspace`. Docker
stores it independently of the container and the host checkout. Operator may
inspect explicitly approved files through its file tools, but it has no local
terminal or code-execution tool.

- `docker compose down` and container recreation preserve the workspace.
- `docker compose down --volumes` or deleting the named volume erases it.
- Only place repositories there that the user explicitly trusts. The initial
  allowlist contains `Welladino/Horology`.
- Unknown repositories, forks, pull requests, new dependencies and unfamiliar
  build or installation scripts belong in Explorer's isolated Modal
  environment.

Inspect the workspace and its clean remote URL:

```bash
docker exec horology-hermes ls -la /workspace
docker exec --user hermes horology-hermes git -C /workspace/Horology remote get-url origin
docker exec --user hermes horology-hermes git -C /workspace/Horology status --short
```

## Dashboard and credential changes

The root `.env` supplies Docker Compose and dashboard settings. Ignored files
under `hermes/` hold model, Modal and connector credentials for their respective
profiles; the bootstrap copies them into the Docker data volume without adding
them to Git.

After changing root `.env`, recreate the container:

```bash
docker compose up -d
```

For tracked profile or skill changes, rerun the bootstrap instead.

## Update Hermes safely

Hermes is pinned through `ops/hermes/Dockerfile`. Do not change the Compose
image to floating `latest`.

Before changing `HERMES_VERSION` or the pinned Modal dependency:

1. Read the upstream release notes and confirm the Modal version required by
   that release.
2. Stop Hermes and back up both `horology-hermes-data` and
   `horology-hermes-workspace`. A Git clone restores reviewed configuration,
   not runtime state or credentials.
3. Build and inspect the replacement image:

   ```bash
   docker compose build --no-cache hermes
   docker run --rm --entrypoint /opt/hermes/.venv/bin/hermes horology-hermes:v0.22.5-modal --version
   ```

4. Recreate Hermes, inspect `docker compose logs hermes`, and verify Operator,
   Explorer, the trusted checkout and a disposable Modal command.
5. Keep `database.journal_mode: delete` in every tracked profile unless a later
   Hermes migration explicitly requires otherwise.

Hermes v0.22 uses one multiplexed host gateway. Do not restore the old
per-profile gateway command; Compose must run `hermes gateway run`.

## Cron scripts

Cron `--script` files are maintained under repository `scripts/`, then copied
to `/opt/data/scripts/` in the container. The bootstrap does not install cron
scripts. After changing one:

```bash
docker cp scripts/check_unembedded_documents.py horology-hermes:/opt/data/scripts/check_unembedded_documents.py
```

The document-graph sweep job is **paused**. Do not resume it merely because
Hermes or its image was updated.

Scripts run under Hermes' bundled Python or Bash, not the repository virtual
environment. Cron scripts do not inherit Hermes-managed provider secrets; any
required plain container environment variable must be set in Compose. A
script's final `{"wakeAgent": false}` output skips the agent turn for that run;
`--no-agent` makes the script itself the entire job.

## Troubleshooting

| Problem | What to check |
|---|---|
| Container exits | Run `docker compose logs hermes`; check the tracked profile configuration and required root `.env` values. |
| Skill is missing | Rerun the bootstrap, list Operator skills and start a new session or use `/reload-skills`. |
| MCP tools are missing | List Operator MCPs, check `tools.include` in `hermes/operator/config.yaml`, then use `/reload-mcp` or start a new session. |
| Operator has no terminal | This is intentional. Route code execution to Explorer instead of enabling local terminal access. |
| Modal terminal is unavailable | Follow the authentication, image and profile checks in the [Modal sandbox troubleshooting guide](modal_sandbox.md#troubleshooting). |
| A tracked change is absent at runtime | Edit the repository source and rerun the bootstrap; do not treat files inside the Docker volume as maintained source. |

Useful inspection commands:

```bash
docker compose logs hermes
docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator skills list
docker exec --user hermes horology-hermes /opt/hermes/.venv/bin/hermes -p operator mcp list
```
