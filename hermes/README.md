# Hermes configuration

This folder contains the reviewed, Git-tracked configuration for the Coordinator, Operator and Explorer profiles. The live Coordinator is Hermes' protected `default` profile with a presentation-only display name. Real `.env` files live beside the examples but are ignored by Git.

- **Coordinator** — user-facing planning, approval, Kanban routing and synthesis.
- **Operator** — non-code research, browser, documents and connected-service work.
- **Explorer** — code execution and dependency experiments in ephemeral Modal sandboxes.

Live sessions, databases, logs, caches and generated gateway files stay in the Docker volume `horology-hermes-data`. The old ignored `hermes-data/` directory is retained as a rollback copy for now.

## Set up on a new machine

You need Git and Docker Desktop with Docker Compose v2. You do **not** need to
clone the upstream Hermes source: Docker builds the local image from the pinned
`nousresearch/hermes-agent` base image.

From the repository root, run:

```bash
./scripts/ops/hermes/bootstrap.sh
```

On its first run, the script creates ignored local `.env` files from the
tracked examples and stops. Fill the required values, then run the same command
again. The script will:

1. build and start the pinned Hermes image;
2. create Operator and Explorer if they are missing;
3. install the tracked profile identities, descriptions and configuration;
4. install the shared Horology skills for Coordinator and Operator, remove the
   subscription-agent supervisor from both, and install the Hermes-only
   Coordinator skill for Coordinator;
5. copy the local ignored credentials into the appropriate profiles; and
6. select Coordinator and restart Hermes.

The script is safe to rerun. It updates reviewed files and skill contents but
does not delete sessions, memories, workspace files, OAuth tokens or other
runtime state.

After it finishes, open <http://127.0.0.1:9119>. OAuth-based MCP servers still
require an interactive login on the new machine. PATs, API keys, Modal tokens,
dashboard credentials, sessions and OAuth tokens are never restored from Git.

## Local credential files

- `.env` at the repository root supplies Docker Compose values.
- `hermes/.env` supplies Coordinator's provider and connector values.
- `hermes/operator/.env` supplies Operator's provider and connector values.
- `hermes/explorer/.env` supplies Explorer's provider and Modal values.

All three real files are ignored. Only their `.env.example` templates are
tracked.

After intentionally changing a tracked profile file, rerun the bootstrap to
apply it. Coordinator maps to `/opt/data`; named profiles map below
`/opt/data/profiles/`.

The shared skill sources remain under `plugins/horology-*`. Coordinator's
Hermes-only routing skill is maintained at
`plugins/horology-hermes/skills/horology-coordinator/SKILL.md`. It is excluded
from the Claude and Codex subscription-agent distributions.
