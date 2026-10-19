# Architecture

How Horology works today. These pages are updated in place when the system changes; the reasons behind each change are in [`docs/planning/`](../planning/README.md), and the commands to run things are in [`docs/runbook/`](../runbook/).

![Horology system map](diagrams/system_map.svg)

Horology has two ways of working, which share the same services:

- **Hermes agents** run locally in Docker. Second-Soul, the supervisor, hands work to named subagent profiles through kanban tasks.
- **Subscription agents** are Claude, ChatGPT and Codex sessions on personal subscriptions. They follow the Horology skills (uploaded to claude.ai for Claude, plugins for Codex) and keep their records in Drive and Sheets.

Both reach the outside world only through two MCP services: the **gateway** (capped provider tools) and the **document graph** (what has been researched and decided). Neither exposes arbitrary SQL or API access.

## Pages

| Area | What it covers |
|---|---|
| [Hermes](hermes/README.md) | Containers, kanban dispatch, profiles and personas, tools and limits |
| [Subscription agents](subscription-agents/README.md) | Stages, registers and IDs, ClickUp sync, skills and connectors |
| [Apps Script projects](subscription-agents/apps-script.md) | Pipeline decisions, the Locations script and the ClickUp sync: what each does and where its settings live |
| [MCP services](mcp/README.md) | What the two services share: sign-in, local and cloud copies, logging and errors |
| ↳ [Gateway](mcp/gateway.md) | Tools, shared policy, credit budgets, provider boundaries |
| ↳ [Document graph](mcp/document-graph.md) | Documents, passage search, topics, entities, the sync job |
| [Data](data/README.md) | The Neon database: schemas, logins and migrations |
| [Cloud](cloud/README.md) | GCP project, Cloud Run, identities, secrets, release gates |

## Where the code lives

| Path | Component |
|---|---|
| `plugins/` | Skill source in four folders (`horology-tools`, `horology-document-graph`, `horology-workflows`, `horology-specialists`), with the OpenAI/Codex plugin manifests |
| `mcp-servers/mcp-gateway/` | Gateway service |
| `mcp-servers/document-graph/` | Document-graph service |
| `document-graph-core/` | Graph logic shared by the document-graph service and the sync job |
| `jobs/document-graph-sync/` | Document Index sync job |
| `shared-runtime/` | Database pool, Google sign-in, settings, logging and errors for every service |
| `alembic/` | Database migrations |
| `google_appscript/clickup-sync/` | Sheets ↔ ClickUp sync |
| `cloudbuild.yaml`, `.github/workflows/` | Release and CI gates |
| `ops/gcp/` | IAM, monitoring and Artifact Registry clean-up configuration |

## Diagrams

Each diagram is described in `diagrams/src/<name>.json` and rendered to `diagrams/<name>.svg` (follows light or dark mode, used in these pages) and `<name>.png` (light, for Drive or Docs). `subscription_workflow` is generated from `workflow.yaml` by `scripts/docs/workflow_diagram.py`; don't edit its description by hand. After editing a description:

```bash
python3 scripts/docs/render_diagrams.py
```
