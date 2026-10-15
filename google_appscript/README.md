# Google Apps Script

Google Apps Script integration infrastructure for workflows using existing ChatGPT/Codex and Claude subscriptions
for Welladino research, assessment and planning. The aim is to use available
subscription capacity before adding recurring model API costs. Availability,
scheduling and usage limits depend on the selected platform and account.

## Responsibilities

- Google Sheets Pipeline records work, stage, agent selection and review status.
- Drive holds research, direction, assessments and plans.
- Decision Register records founder decisions and rework instructions.
- Document Index associates documents with permanent Pipeline IDs and revisions.
- ClickUp presents Pipeline tasks and review status.
- Subscription agents perform selected work using shared workflow skills.
- Apps Script transfers records between Sheets and ClickUp; it does not run AI.

Flow: capture → Stage 1 proposal → Stage 2 decision → rework or Stage 3
specialist deliverable → review. Approval of a code proposal authorises its
planning-note deliverable, not automatic implementation.

## Components

| Folder | Purpose | Runtime |
| --- | --- | --- |
| [Workflow plugin](../plugins/horology-workflows/) | Shared capture, research and technical-assessment instructions | Loaded by the selected agent platform |
| [clickup-sync](clickup-sync/README.md) | Modular Sheets/ClickUp sync and document lookup | Google Apps Script |

The files here are versioned in Horology, but do not depend on a running Hermes
container or a deployed Horology server. Existing Hermes personas, MCP servers
and Neon document graph remain separate. Backfill and further integrations can
be added when needed; this folder does not enable them.

Workflow skill source and plugin metadata live together in `plugins/horology-workflows/`.

Maintain each component locally, test it, review the Git diff and publish only
the selected component. Keep credentials outside Git and record meaningful
workflow changes in the repository planning notes.

Current design: [architecture](../docs/architecture/subscription-agents/README.md). Maintenance and publishing: [runbook](../docs/runbook/subscription-agents/README.md).
