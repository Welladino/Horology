---
name: horology-supervisor
description: Run Pipeline items that are Ready. Dispatch mode finds Ready rows for this platform, claims them in the Runs tab and starts one session per item, locally or in the cloud. Item mode handles one item end to end — reads it, chooses the specialist skills, runs them, checks the results and saves. Use when asked to run the Ready items or to run a specific item.
---

# Supervisor

## When to use

- "Run the Ready items" or "what's Ready?": **dispatch** mode.
- "Run item 42", or a session started by dispatch for one item: **item** mode.

The founder starts runs; nothing here runs on its own. The supervisor chooses and coordinates; the specialist skills from the Horology Specialists plugin do the work.

## Required context and locations

- Read the current [Workflow Guide](https://docs.google.com/document/d/1CdytxCa2c-M7KroQ05JO52_mVhogQ5J_acBhRDRsF5I/edit) and [Agent Location Directory](https://docs.google.com/document/d/1LZjDIqlRGYZjw_f1XgfEWzLqKOMjNWBS4Fz9afw18Ao/edit).
- Read [routing rules](references/routing.md) before choosing specialists, and [runs and steps](references/runs.md) before claiming or recording a run.
- Pipeline field rules are in the capture-triage skill's [records reference](../horology-capture-triage/references/records.md). Map live headers by name; columns move.
- When the document-graph connector is available, use the `horology-document-graph` skill to check what already exists. Say so when it isn't available.

## Dispatch mode

1. Work out which platform you're running on: **Claude Code** or **Codex**. Only take rows whose Agent type matches it. Never run another platform's rows.
2. Read Pipeline Master. Select rows with Agent status **Ready** and your Agent type. Skip rows with a live claim in the Runs tab (status claimed or running, and Claim expires still in the future).
3. For each selected item, add a Runs row (claimed, with a 2-hour claim) as described in [runs and steps](references/runs.md).
4. Start one session per item, by the row's **Run location** (blank means Local). Pass the Pipeline ID and the run ID. Commands are in [runs and steps](references/runs.md).
5. If you can't run shell commands here (for example claude.ai chat), run each item yourself in item mode, one at a time, using a subagent per item where the platform allows.
6. Report the items started, where each runs, and the session links. Local sessions return their final answer when they finish; cloud sessions return only a link, and their results land in the registers.

## Item mode

For exactly one Pipeline ID:

1. If you were started without a run ID, claim the item first (step 3 of dispatch). If the Runs row shows a live claim by another run, stop and report it.
2. Set the Runs row to **running**. Read the Pipeline row: Title, Domain, Type, Status, Stage, Next step / Research question, Current decision ID and the target (Link type, URL, GitHub branch).
3. If Current decision ID is set, read that Decision Register row, including rework instructions. If the Steps tab has steps for this item, follow them in order.
4. Search the document graph for earlier research, decisions, topics and entities on the subject. Note what is already answered.
5. Choose the specialist skill(s) for the question, or for each step (see routing rules). If nothing fits, stop, record why in the Runs row and report it.
6. Run each specialist as a subagent with the Pipeline ID, the bounded question and the instruction to follow its skill. Run independent ones side by side, dependent ones in order. Where subagents aren't available, follow the skills yourself one after another.
7. Check each result (see routing rules). Send weak work back once with specific gaps, then report what remains.
8. Confirm the specialists saved their Drive outputs, Document Index rows and proposed decision, and that the item is Awaiting decision only when the work is ready for review. Mark completed steps done.
9. Close the Runs row: done or failed, finished time, skills used, plan reason, output document IDs and notes.

## Decision and permission boundaries

- The founder decides. Never accept, reject or park a proposal, and never record a decision as accepted.
- Only run rows that are Ready. Never set an item to Ready, and never change Agent type or Run location.
- Ready selects work; it doesn't authorise implementation or anything beyond the stated next step.
- Don't edit the Agent Register.

## Output requirements

- Dispatch: the items started, their run IDs, run location and session links, and any skipped (claimed, wrong platform) with the reason.
- Item: the specialists used, where outputs were saved, the result of your check, and anything blocked or pending.

## Verification before finishing

- Read back the Runs row and any Pipeline cells you wrote; confirm unrelated cells were preserved.
- Confirm every specialist skill you named is installed. Report any that aren't.
- Distinguish saved changes from pending work.
