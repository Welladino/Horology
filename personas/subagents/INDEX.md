# Subagent Index

The Hermes table has one line per subagent: profile name (used as the kanban `--assignee`), one-line scope. Each is a real, persistent Hermes profile — its own identity, model, memory — not an ephemeral delegation. Second-Soul reads this file to decide *which* profile fits a task, then assigns a kanban task to it. The `.md` file in this folder for each subagent is the source-of-truth persona content, kept in sync with that profile's own `SOUL.md` (see `docs/runbook/`) — it is not re-injected per task the way it was under the old `delegate_task` mechanism.

Adding a subagent = create a real Hermes profile (`hermes profile create <name>`), write its persona into a new `.md` file here, sync it to the profile's `SOUL.md`, connect the document-graph MCP server to that profile, and add one row here.

| Profile name | Scope | Persona source |
|---|---|---|
| gtm-manager | Positioning, channel/market strategy, sequencing, pricing-adjacent strategic questions | `/opt/data/personas/subagents/gtm-manager.md` |
| marketing-executive | Copy, content drafts, campaign execution, messaging | `/opt/data/personas/subagents/marketing-executive.md` |
| code-sentinel | CI status, open PRs, dependency security alerts, code quality for policy-approved repositories (read-only GitHub gateway) | `/opt/data/personas/subagents/code-sentinel.md` |

## Subscription-agent prompt sources

These prompts were moved from Welladino — Agent Register, Master. They are not provisioned Hermes profiles; they use the Drive/Sheets subscription workflow and do not inherit the Hermes document-graph/kanban requirements above. GitHub links in the register will be added after source publication.

| Register ID | Agent | Platform | Skill | Persona source |
|---|---|---|---|---|
| 1 | Research | ChatGPT | welladino-research | [research.md](research.md) |
| 2 | Technical Assessment | ChatGPT | welladino-technical-assessment | [technical-assessment.md](technical-assessment.md) |
