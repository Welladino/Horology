# Subscription-agent operations

Read [architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/subscription-agents.md) for responsibilities and stages. These steps maintain skills and the Sheets/ClickUp integration; they do not deploy Hermes or start AI schedules.

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

Edit [`workflow.yaml`](https://github.com/Welladino/Horology/blob/main/plugins/horology-workflows/skills/horology-capture-triage/references/workflow.yaml) first, then the skills or Apps Script code that apply the changed rule, and the Mermaid workflow diagrams in the [subscription-agents page](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/subscription-agents.md). Then check:

```bash
.venv/bin/python -m pytest tests/unit/workflow -q
```

The tests fail if a move or status in `workflow.yaml` is missing from the diagrams.

## Run Ready items

Set the item's Agent status to Ready, Agent type to Claude Code or Codex, and Run location to Local or Cloud (blank means Local). Then, in a Claude Code or Codex session opened in the Horology repository:

> Use horology-supervisor to run the Ready items.

or for one item:

> Use horology-supervisor to run Pipeline item 42.

The supervisor claims each item through the document graph and starts one session per item. Check progress by asking a session to `list_runs`, or `get_item_history` for one item. Every run needs the document-graph connector. Claude cloud runs need the skills and the document graph and Google connectors on your claude.ai account. Codex runs need the Codex CLI installed and signed in.

## Decide on an item

Open the [Horology workspace](https://script.google.com/a/macros/welladino.com/s/AKfycbz3M-ONEZF3ox378oBdoecMb0wV7WdJNZX0jQgrq7NAEDqRZbs0OVCuYPgob7qrPWrr2Q/exec) while signed into the Google account that owns the Pipeline Apps Script, or use **Extensions → Horology — Pipeline decisions → Open Horology workspace** and click its link. In **Decisions**, expand a Pipeline row and open a decision to compare the options and evidence and choose an outcome. For a different option, edit **Decision to record** so its conditions are accurate, then give a short reason. **Save decision** writes to Decision Register Master and applies that item's Pipeline transition immediately; the page reports if the Pipeline update is pending.

Use **Pipeline** to browse all Master rows as Cards or Rows. Search the text or filter by Domain and Status. Expand **More filters** for Entity, Type, Agent status, Agent type, Run location and Stage; **Clear filters** resets the search and filters. Open an item to see its next step, revisit trigger and links. Choose **Edit item** to change its title, type, summary, next step, revisit trigger or agent assignment, then **Save item**. Domain, Entity, Status and Stage are displayed without edit controls. If another writer changed the item, refresh it before saving.

In **Decisions**, expand a Pipeline item to see its decisions, then choose a decision to review it or read its recorded outcome and reason.

To capture new work, choose **Add Pipeline item** in the same page. Fill Title and Domain, then optionally add the reason, next step, revisit trigger and target. Ready items need an agent and a Next step. **Add item** writes the next permanent ID to Pipeline Master. The old Add Pipeline item entry is no longer in the Workbook Extensions menu.

The existing sheet route also works: in the Decision Register, set the current decision's Status to accepted, rework (with Rework instructions), parked or rejected. The [Pipeline decisions](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md#pipeline-decisions) script moves the Pipeline item within 10 minutes, or straight away when you edit the register yourself. To check, inspect the item’s Status in the Pipeline or run `previewDecisions` from the Apps Script editor as an administrator.

## Scheduled jobs

Create the oversight jobs below on a platform scheduler. Investigation and Stage 3 runs remain founder-started. During a Stage 3 run, the supervisor invokes Horology Synthesis Artifacts immediately after saving the deliverable, then presents both outputs for review. No Stage 4 schedule or second founder prompt is needed.

| Job | When | Prompt |
|---|---|---|
| Digest | Daily | `Use horology-digest to write today's Horology digest.` |
| Planner | Daily, or on request | `Use horology-planner to plan the Pipeline items set to Plan.` |

The scheduled session needs the skills (claude.ai skills for Claude, the installed plugin for Codex) and Drive, Docs and Sheets access. An empty Plan list means the planner run ends quickly.

## Maintain ClickUp integration

Use the [Apps Script runbook](clasp.md) to connect, compare and publish the Apps Script projects and set up ClickUp Sync. The [Apps Script architecture](https://github.com/Welladino/Horology/blob/main/docs/architecture/subscription-agents/apps-script.md) describes decision rules, the Drive check, and one-way ClickUp status and milestone comments.
