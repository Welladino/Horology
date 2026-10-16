# Subscription-agent operations

Read [architecture](../../architecture/subscription-agents/README.md) for responsibilities and stages. These steps maintain skills and the Sheets/ClickUp integration; they do not deploy Hermes or start AI schedules.

## Live records and instructions

- [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit)
- [Agent Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit)
- [Presentation Guide](https://docs.google.com/document/d/1D2N9VJRCmBFJ4T9cUGH47zQUVqk99sjavpbbwYIYY8I/edit)
- [Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit)
- [Decision Register](https://docs.google.com/spreadsheets/d/1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE/edit)
- [Document Index](https://docs.google.com/spreadsheets/d/1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc/edit)

## Maintain and install skills

Edit source in `plugins/horology-workflows/skills/` and `plugins/horology-specialists/skills/`. Read each SKILL.md and its linked references. Update live-field guidance when the workflow changes, keeping exact column positions out of instructions.

For local Codex copies, run from the Horology root:

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
for dir in plugins/horology-workflows/skills/* plugins/horology-specialists/skills/*; do
  skill=$(basename "$dir")
  mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/$skill"
  cp -R "$dir/." "${CODEX_HOME:-$HOME/.codex}/skills/$skill/"
done
```

Ensure destination skill directories exist before copying. Start a fresh session to verify discovery. Keep source and installed copies distinct. The old shared-folder skill paths are compatibility symlinks; maintain only the Horology source.

Cloud sessions cannot read these local paths automatically. Package these source folders into the Welladino workflow plugin and update it through its supported publishing process. Do not edit a downloaded plugin cache as a release. Configure Drive/Sheets access separately and test loading the skills plus reading the guides/registers before allowing writes. Claude and other runners need their own supported loading/install mechanism.

## Change the workflow

Edit [`workflow.yaml`](../../../plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml) first, then the skills or sync code that apply the changed rule. Check and redraw:

```bash
.venv/bin/python -m pytest tests/unit/workflow -q
```

```bash
.venv/bin/python scripts/docs/workflow_diagram.py
```

## Run Ready items

Set the item's Agent status to Ready, Agent type to Claude Code or Codex, and Run location to Local or Cloud (blank means Local). Then, in a Claude Code or Codex session opened in the Horology repository:

> Use horology-supervisor to run the Ready items.

or for one item:

> Use horology-supervisor to run Pipeline item 42.

The supervisor claims each item through the document graph and starts one session per item. Check progress by asking a session to `list_runs`, or `get_item_history` for one item. Every run needs the document-graph connector. Cloud runs need the Horology repository on GitHub, the skills under `.claude/skills/`, and the document graph and Google connectors on your claude.ai account. Codex runs need the Codex CLI installed and signed in.

## Decide on an item

In the Decision Register, set the current decision's Status to accepted, rework (with Rework instructions), parked or rejected. The [pipeline-decisions](../../../google_appscript/pipeline-decisions/README.md) script moves the Pipeline item on within 10 minutes, or straight away when you edit the register yourself. To check: run `previewDecisions` in its Apps Script project, or look at the item's Status.

## Scheduled jobs

Create these on any platform's scheduler (Claude Code routine or desktop scheduled task, Cowork, Codex automation). They report or prepare; they never run items.

| Job | When | Prompt |
|---|---|---|
| Digest | Daily | `Use horology-digest to write today's Horology digest.` |
| Planner | Daily, or on request | `Use horology-planner to plan the Pipeline items set to Plan.` |

The scheduled session needs the skills (installed plugin, or `.claude/skills/` for a cloud routine) and Drive, Docs and Sheets access. An empty Plan list means the planner run ends quickly.

## Maintain ClickUp integration

Use the [clasp runbook](clasp.md) to connect, inspect, compare and publish Apps Script source. The [sync workflow](../../../google_appscript/clickup-sync/WORKFLOW.md) defines schema, status mapping, preview and apply behaviour.
