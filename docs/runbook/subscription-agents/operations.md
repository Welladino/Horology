# Subscription-agent operations

Read [architecture](../../architecture/subscription-agents/README.md) for responsibilities and stages. These steps maintain skills and the Sheets/ClickUp integration; they do not deploy Hermes or start AI schedules.

## Live records and instructions

- [Pipeline Locations](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit#gid=2040100904): folders; Domains, Templates and Registers are tabs of the same workbook
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

Cloud sessions cannot read these local paths. For Claude, upload the skills and add the connectors on claude.ai ([Claude skills and connectors](claude_skills.md)). For Codex, package these source folders into the Welladino workflow plugin and update it through its supported publishing process. Do not edit a downloaded plugin cache as a release. Configure Drive/Sheets access separately and test loading the skills plus reading the guides/registers before allowing writes.

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

The supervisor claims each item through the document graph and starts one session per item. Check progress by asking a session to `list_runs`, or `get_item_history` for one item. Every run needs the document-graph connector. Claude cloud runs need the skills and the document graph and Google connectors on your claude.ai account. Codex runs need the Codex CLI installed and signed in.

## Decide on an item

In the Decision Register, set the current decision's Status to accepted, rework (with Rework instructions), parked or rejected. The [Pipeline decisions](../../architecture/subscription-agents/apps-script.md#pipeline-decisions) script moves the Pipeline item on within 10 minutes, or straight away when you edit the register yourself. To check: use **Extensions → Horology — Pipeline decisions → Preview decisions** in the Pipeline, or look at the item's Status.

## Scheduled jobs

Create these on any platform's scheduler (Claude Code routine or desktop scheduled task, Cowork, Codex automation). They report or prepare; they never run items.

| Job | When | Prompt |
|---|---|---|
| Digest | Daily | `Use horology-digest to write today's Horology digest.` |
| Planner | Daily, or on request | `Use horology-planner to plan the Pipeline items set to Plan.` |

The scheduled session needs the skills (claude.ai skills for Claude, the installed plugin for Codex) and Drive, Docs and Sheets access. An empty Plan list means the planner run ends quickly.

## Maintain ClickUp integration

Use the [Apps Script runbook](clasp.md) to connect, compare and publish the Apps Script projects and set up ClickUp Sync. The [Apps Script architecture](../../architecture/subscription-agents/apps-script.md) describes their behaviour: decision rules, the Drive check, and the sync's status mapping, review and batching.
