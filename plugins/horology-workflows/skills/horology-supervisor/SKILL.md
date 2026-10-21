---
name: horology-supervisor
description: Start here for any request about Pipeline work unless a specific skill is named — running, planning, scoping or continuing an item, or asking what ran and what it found. Dispatch mode finds Ready rows for this platform, claims them and starts one session per item, locally or in the cloud. Item mode handles one item end to end — reads it, chooses the specialist skills, runs them, checks the results and saves. Status mode reports what is running, what finished and what it found, and answers questions about it. Sends items that need scoping to the planner.
---

# Supervisor

## When to use

- "Run the Ready items": **dispatch** mode.
- "Run item 42", or a session started by dispatch for one item: **item** mode.
- "What's happening?", "what's Ready?", "what did the runs find?", "how did item 42 go?": **status** mode. It only reads; it starts and changes nothing.
- "Plan item 42", "scope this", "split it up": **planning**. With the founder's go-ahead in the conversation, set the item's Agent status to Plan and use the `horology-planner` skill on it.
- Any other request to work on or continue a Pipeline item, when no skill is named: read the item, say which of these fits and why, then do it. If it isn't Ready to run, say what it needs (Ready to run, Plan to scope) and ask.

The founder starts investigation and Stage 3 runs. Within each Stage 3 run, the supervisor invokes the `horology-synthesis-artifacts` specialist immediately after the deliverable is saved. No new founder prompt, Ready selection or schedule starts Stage 4. The supervisor chooses and coordinates the specialists.

## Required context and locations

- Read [domains, folders and templates](../horology-capture-triage/references/locations.md) before choosing a domain or entity, reading context or saving anything.
- Read [routing rules](references/routing.md) before choosing specialists, and [runs](references/runs.md) before claiming or finishing a run.
- Pipeline field rules are in the capture-triage skill's [records reference](../horology-capture-triage/references/records.md). Map live headers by name; columns move.
- The document-graph connector is required: claims and run records go through it. If it isn't available, stop and say so. Use the `horology-document-graph` skill to check what already exists.

## Dispatch mode

1. Work out which platform you're running on: **Claude Code** or **Codex**. Only take rows whose Agent type matches it. Never run another platform's rows.
2. Read Pipeline Master. Select rows with Agent status **Ready** and your Agent type.
3. Claim each selected item with `claim_item` (kind `run`, the row's Run location) as described in [runs](references/runs.md). Skip items another run holds.
4. Start one session per item, by the row's **Run location** (blank means Local). Pass the Pipeline ID and the run ID. Commands are in [runs](references/runs.md).
5. If you can't run shell commands here (for example claude.ai chat), run each item yourself in item mode, one at a time, using a subagent per item where the platform allows.
6. Report the items started, where each runs, and the session links. Local sessions return their final answer when they finish; cloud sessions return only a link, and their results land in the registers.

## Item mode

For exactly one Pipeline ID:

1. If you were started without a run ID, claim the item first with `claim_item`. If another run holds it, stop and report it.
2. Set the item's Status to **Researching**. Read the Pipeline row: Title, Domain, Type, Status, Stage, Next step / Research question, Current decision ID and the target (Link type, URL, GitHub branch).
3. If Current decision ID is set, read that Decision Register row, including rework instructions. If Next step is a numbered list of steps, follow them in order.
4. Search the document graph for earlier research, decisions, topics and entities on the subject. Note what is already answered.
5. Choose the specialist skill(s) for the question, or for each step (see routing rules). If the question is too vague or broad for one run, finish the run as failed, say so, and recommend Plan. If nothing fits, finish the run as failed with the reason and report it.
6. Run each specialist as a subagent with the Pipeline ID, the bounded question and the instruction to follow its skill. Run independent ones side by side, dependent ones in order. Where subagents aren't available, follow the skills yourself one after another.
7. Check each result (see routing rules). Send weak work back once with specific gaps, then report what remains.
8. Confirm the specialists saved their Drive outputs, Document Index rows and proposed decision. For Stage 1, set Status **Awaiting decision**, Stage **Stage 2** and Review stage **Investigation proposal**.
9. For Stage 3, invoke `horology-synthesis-artifacts` in this same run after the specialist output is verified. Pass the Pipeline ID, run ID and source links. Verify the visual artifact in the Synthesis folder and its Document Index row; then set Status **Awaiting decision**, Stage **Stage 4** and Review stage **Specialist deliverable**. Return the Stage 3 output and Stage 4 visual briefing together for founder review. If synthesis fails, leave the Stage at **Stage 3**, report the error and finish the run as failed; do not silently present Stage 3 as the finished result.
10. Set Agent status back to **No action** when the run ends. Then call `finish_run`: done or failed, skills used including synthesis when run, steps done and notes. Status changes and outputs are recorded from the sheets.

The allowed moves are defined in [workflow.yaml](../horology-capture-triage/references/workflow.yaml); don't make others.

## Status mode

The founder talks to you instead of each session. Answer from what the runs recorded and saved:

1. Call `list_runs` for the period asked about (default the last 24 hours), or for one `pipeline_id`.
2. Sort the runs into:
   - **Running:** status claimed and not expired. You can't see progress inside a running session; give its start time, location and session link.
   - **Finished:** status done. `list_runs` gives only an output count; get the outputs from `get_item_history` for that item, open them (Drive documents from their Document Index rows; agent documents with `get_document`) and give the key finding and recommendation in a sentence or two each.
   - **Failed or died:** status failed (give its notes), or a claim that expired without finishing (the session stopped; the item can be run again).
3. Add what's waiting on the founder: Ready rows not yet claimed (by Agent type and Run location), Plan rows, and items Awaiting decision.
4. For one item, use `get_item_history` for its full timeline. Flag changes marked `expected: false`.
5. Answer follow-up questions from the saved outputs, and say when something isn't in them. A session's conversation isn't recorded; only what it saved, its `finish_run` notes and the status changes are. To see or steer a running session, give its session link.

Skills used, steps done and notes are reported by the session itself; outputs and status changes come from the sheets. Say which you are relying on when it matters.

## Decision and permission boundaries

- The founder decides. Never accept, reject or park a proposal, and never record a decision as accepted.
- Only run rows that are Ready. Never set an item to Ready, and never change Agent type or Run location. Always return a run item to No action when its run ends.
- Stage 4 synthesis is the final specialist in a Stage 3 run. It does not make an item Ready or change a founder decision.
- Ready selects work; it doesn't authorise implementation or anything beyond the stated next step.
- Don't edit the Agent Register.

## Output requirements

- Dispatch: the items started, their run IDs, run location and session links, and any skipped (claimed, wrong platform) with the reason.
- Item: the specialists used, where outputs were saved, the result of your check, and anything blocked or pending.
- Status: running, finished (with findings and links), failed or died (with the reason), and waiting on the founder, in that order. Keep it short; offer detail on request.

## Verification before finishing

- Confirm `finish_run` was accepted. Read back any Pipeline cells you wrote and confirm unrelated cells were preserved.
- Confirm every specialist skill you named is installed. Report any that aren't.
- Distinguish saved changes from pending work.
