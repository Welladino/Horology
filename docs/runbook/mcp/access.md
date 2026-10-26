# Users, workspaces and MCP access

Who may use which MCP server, and which workspaces each person can open, live in Neon, in the `access` schema (`users`, `workspaces`, `workspace_members`, `user_mcp_access`, `mcp_servers`). Manage them with `scripts/ops/mcp/access.py`, which uses the owner connection (`DATABASE_URL` in the root `.env`, as for migrations). Running services pick up a change within 5 minutes. Design: [brief](https://github.com/Welladino/Horology/blob/main/docs/planning/research/2026-10-16_users-workspaces-and-mcp-access_research.md).

Run from the repository root:

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py user list
```

## Add a person

1. Google Auth Platform → Audience (`horology-dev`) → Test users → **Add users**. Keep publishing status **Testing** (at most 100 test users).
2. Add them, put them in a workspace and grant the servers they need:

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py user add person@example.com --note "Contractor, Q4"
```

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py member add person@example.com welladino
```

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py grant person@example.com document-graph
```

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py grant person@example.com gateway
```

Current operating rule: one email belongs to one workspace. The database can hold multiple memberships for future use, but private Pages publishing refuses an email with zero or multiple active memberships. The document graph still has its workspace picker for such accounts.

## Remove a person

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py user disable person@example.com
```

Both servers refuse them within 5 minutes. To cut the gateway off at once, also revoke their gateway tokens with `mcp-servers/mcp-gateway/scripts/revoke_email.py` (see the [deployment runbook](../gcp/mcp_deployment.md#add-or-remove-a-person)), and remove them from the Audience test users so they can't sign in again. `revoke` and `member remove` take away one server or workspace.

## Add a workspace

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py workspace add client-x "Client X" --index DOCUMENT_INDEX_ID --pipeline PIPELINE_ID --decisions DECISION_REGISTER_ID
```

Names are lowercase letters, digits and hyphens. Share the spreadsheets with the sync job as described in the [deployment runbook](../gcp/mcp_deployment.md#add-a-workspace). The sync job syncs every active workspace with a Document Index; `workspace set` changes the sheet IDs, `workspace disable` stops it.

Private synthesis publishing is a separate setup: the administrator must protect the workspace's Pages project and both hostnames with Cloudflare Access, then register and enable its mapping with `scripts/ops/mcp/pages.py`. See the [workspace Pages note](../../planning/notes/2026-10-22_workspace-pages-publishing_note.md). A new workspace without that setup can still use its other tools; `publish_synthesis` returns an administrator-contact message instead of uploading.

## Add an MCP server

1. Add its row:

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py server add new-server "New server"
```

2. In the server's code, build `horology_runtime.access.Directory(database, 'new-server')` and pass its `check` to the shared Google sign-in (and `workspaces` if it is workspace-scoped), as the gateway and document graph do. Give its database login USAGE on schema `access` and SELECT on its tables in a migration.
3. Grant people access with `grant EMAIL new-server`. `server disable` closes a server to everyone.

## See the current state

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py workspace list
```

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py server list
```

```bash
.venv/bin/dotenv run -- .venv/bin/python scripts/ops/mcp/access.py user show person@example.com
```
