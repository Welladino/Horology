# Subscription-agent operations

Read [architecture](../../architecture/subscription_agents.md) for responsibilities and stages. These steps maintain skills and the Sheets/ClickUp integration; they do not deploy Hermes or start AI schedules.

## Live records and instructions

- [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit)
- [Agent Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit)
- [Presentation Guide](https://docs.google.com/document/d/1D2N9VJRCmBFJ4T9cUGH47zQUVqk99sjavpbbwYIYY8I/edit)
- [Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit)
- [Decision Register](https://docs.google.com/spreadsheets/d/1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE/edit)
- [Document Index](https://docs.google.com/spreadsheets/d/1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc/edit)

## Maintain and install skills

Edit source in `plugins/horology-workflows/skills/`. Read each SKILL.md and its linked references. Update live-field guidance when the workflow changes, keeping exact column positions out of instructions.

For local Codex copies, run from the Horology root:

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
for skill in welladino-capture-triage welladino-research welladino-technical-assessment; do
  mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/$skill"
  cp -R "plugins/horology-workflows/skills/$skill/." "${CODEX_HOME:-$HOME/.codex}/skills/$skill/"
done
```

Ensure destination skill directories exist before copying. Start a fresh session to verify discovery. Keep source and installed copies distinct. The old shared-folder skill paths are compatibility symlinks; maintain only the Horology source.

Cloud sessions cannot read these local paths automatically. Package these source folders into the Welladino workflow plugin and update it through its supported publishing process. Do not edit a downloaded plugin cache as a release. Configure Drive/Sheets access separately and test loading the skills plus reading the guides/registers before allowing writes. Claude and other runners need their own supported loading/install mechanism.

## Run one selected item

1. Read live Master headers, selected permanent ID, Agent type/status, stage, bounded scope and target repo/branch when applicable. Skip Manual in scheduled runs.
2. Read guides and the relevant skill; verify tools and destinations are accessible.
3. Produce the authorised deliverable. Copy a template, index the output against Pipeline ID, and preserve decision/document history.
4. Request founder review through the workflow. Rework reads Decision Register feedback; acceptance authorises only the agreed next-stage scope.
5. Read back records and links. Report incomplete saves or access gaps. Do not start implementation, backfill or another stage without authorisation.

Before adding a schedule, verify platform support and access in that environment, choose a bounded selection and stopping point, and prevent overlapping writers. No schedule is installed by these instructions.

## Maintain ClickUp integration

Use the [clasp runbook](clasp.md) to connect, inspect, compare and publish Apps Script source. The [sync workflow](../../../google_appscript/clickup-sync/WORKFLOW.md) defines schema, status mapping, preview and apply behaviour.
