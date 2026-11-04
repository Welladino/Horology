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

Pipeline **Type** chooses the route. Idea, Research, Direction and Plan items take the **investigation route** (Stage 1 proposal, Stage 2 founder decision, Stage 3 deliverable, Stage 4 synthesis, then Completed). Feature, Enhancement, Refactor and Fix items take the **implementation route**: Stage 1 is the implementation plan (a Drive document plus Steps rows), Stage 3 the implementation and its Implementation report, then Completed at Stage 4 with no page unless the founder asks for one; Status **In progress** until then, no Stage 2. Every route starts with a Stage 1 specialist document in Drive plus Steps rows.

The founder starts investigation, implementation and Stage 3 runs. Within each investigation-route Stage 3 run, the supervisor invokes the `horology-synthesis-artifacts` specialist immediately after the deliverable is saved; no new founder prompt, Ready selection or schedule starts Stage 4. On the implementation route the Implementation report is the Stage 4 record and a page is made only on request (founder, 04/11/2026, to save cost). The supervisor chooses and coordinates the specialists.

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
2. Find the item's Pipeline row by its ID (never by row position; other runs write the same sheet). Read the row: Title, Domain, Type, Status, Stage, Next step / Research question, Current decision ID and the target (Link type, URL, GitHub branch). Choose the route from Type and set Status to **Researching** (investigation route) or **In progress** (implementation route; then follow [Implementation route](#implementation-route) instead of steps 5–9). If the live Status dropdown has no In progress yet, stop and report it.
3. If Current decision ID is set, read that Decision Register row, including rework instructions, and its rows on the Decision Register's Options tab. Read the item's planned steps: its rows on the Pipeline's Steps tab (by Pipeline ID, in Step order, skipping Done and Skipped), or else a numbered list in Next step. Follow them in order. At Stage 1 with no open steps, write the steps this run will take as Steps rows first (see [runs](references/runs.md#steps)), on either route.
4. Search the document graph for earlier research, decisions, topics and entities on the subject. Note what is already answered.
5. Choose the specialist skill(s) for the question, or for each step (see routing rules). If the question is too vague or broad for one run, finish the run as failed, say so, and recommend Plan. If nothing fits, finish the run as failed with the reason and report it.
6. Run each specialist as a subagent with the Pipeline ID, the run ID (specialists pass it to `reserve_id` for new Decision and Document IDs), the bounded question and the instruction to follow its skill. Run independent ones side by side, dependent ones in order. Where subagents aren't available, follow the skills yourself one after another.
7. Check each result (see routing rules). Send weak work back once with specific gaps, then report what remains.
8. Confirm the specialists saved their Drive outputs, Document Index rows and proposed decision, and that each register row's Pipeline ID is this item (`get_item_history` lists the IDs this run reserved). Set Current decision ID only to a decision reserved for this item. For Stage 1, confirm the specialist document is in Drive from the template that fits (Research, Direction, Plan or Technical Assessment), then set Status **Awaiting decision**, Stage **Stage 2** and Review stage **Investigation proposal**.
9. For Stage 3, invoke `horology-synthesis-artifacts` in this same run after the specialist output is verified. Pass the Pipeline ID, run ID and source links. Verify the visual artifact in the Synthesis folder; a Stage 4 HTML page has no Document Index row (the Pages tab lists it once published). Then propose a **Specialist deliverable** decision for the deliverable: reserve a Decision ID with `reserve_id`, call `check_register_write`, write a one-line Decision cell (for example "Proposed: accept the Stage 3 deliverable and its Stage 4 briefing"), Review stage **Specialist deliverable**, and one Options row per option (accept, rework, park; the deliverable's own choices where it recommends one), with one Recommended. Set Current decision ID to it. Then set Status **Completed**, Stage **Stage 4** and Review stage **Specialist deliverable** (`synthesize-stage-3`). The item is finished; the founder can accept the decision, or reopen the item from it with rework, park or reject on the decision page. Return the Stage 3 output and Stage 4 visual briefing together. If synthesis fails, leave the Stage at **Stage 3**, report the error and finish the run as failed; do not silently present Stage 3 as the finished result.
10. Mark each completed step's Steps row **Done** (found by Pipeline ID and Step). Set Agent status back to **No action** when the run ends. Then call `finish_run`: done or failed, skills used including synthesis when run, steps done and notes. Status changes and outputs are recorded from the sheets.

## Implementation route

For Feature, Enhancement, Refactor and Fix items, after steps 1–4 of item mode:

1. **Stage 1, plan.** Write the Stage 1 document to Drive: copy the template that fits (usually Plan; Technical Assessment when the change needs options compared first, through `horology-technical-assessment`) into the matching Agent output folder, fill it and add its Document Index row under a reserved Document ID. Skip this only when the item already has a current Stage 1 document, for example on a resumed or reworked run. If the item has no open Steps rows, write the implementation plan as Steps rows (Pipeline ID, Step, Task with what "done" looks like, Specialist blank or a fitting skill, Status Planned), following the planner's Steps rules; the last step is the Implementation report. Keep Next step a one-line summary. Add a repo doc only if the repository already keeps its own docs: in its style, on the item's GitHub branch (never `main` by assumption), naming the Drive document by Document ID, with its link in Related Repo Document. Then set Stage **Stage 3** yourself in the same run; no Stage 2 review.
2. **Stage 3, implement.** Work through the open Steps rows in order. For code, follow the repository's CLAUDE.md or AGENTS.md: a branch, tests, commits, a pushed branch and a pull request; never merge or deploy unless the item says so. Use a specialist skill only for a step that asks for its kind of output. Mark each finished step **Done** as you go (by Pipeline ID and Step), or **Skipped** with the reason in the notes.
3. **Stage 3, report.** When every step is Done or Skipped and nothing needs the founder, copy the **Implementation report** template from the Templates tab and fill it: what changed and why, commits and pull request, tests and checks, changes from the plan, and what's left for the founder. Save it in the same Agent output folder as the item's Stage 1 document, unless a folder's Purpose names implementation reports, and add its Document Index row (Document Type report, Draft) under a reserved Document ID.
4. **Stage 4, decision.** Don't invoke `horology-synthesis-artifacts` or make a page by default (founder, 04/11/2026, to save cost); the Implementation report is the record. Propose a **Specialist deliverable** decision as in item-mode step 9 (Decision cell, for example "Proposed: accept the implementation and its report"; Options accept, rework, park, one Recommended; Research Links the report and the Stage 1 document) and set Current decision ID to it. Then set Status **Completed**, Stage **Stage 4** and Review stage **Specialist deliverable** (`complete-implementation`). Record what was done in `finish_run` notes: branch, commits, pull request, the report link, and anything left for the founder (deploy steps, manual checks). If the report or decision fails, leave Status **In progress** and Stage **Stage 3**, report the error and finish the run as failed; the work stays pushed and the next run makes only what is missing.
   **Page on request.** When the founder asks for a page for an implementation item, invoke `horology-synthesis-artifacts` with the Pipeline ID, the run ID (if any) and the Implementation report and Stage 1 document links. It makes the page from the report, saves the HTML in the Synthesis folder (no Document Index row), publishes it and adds or updates the Pages tab row with the Implementation report's Document ID. It changes no Status, Stage or decision.
5. **Implementation question.** When a step needs a founder choice you can't make from the item, its decision or the repository, stop: commit and push the work so far, save the findings to a Drive document (or add them to the Stage 1 document), then draft a proposed decision (reserve a Decision ID with `reserve_id`; `check_register_write`, passing the Research Links; a one-line Decision cell; Research Links holding the item's Stage 1 document and any findings document, Drive files only, never a commit, compare, branch or repository-file link; Review stage **Implementation question**; one Options row per option with one Recommended), set Current decision ID to it, Status **Awaiting decision**, Stage **Stage 3** and Review stage **Implementation question**, and finish the run as done. The founder answers on the decision page; the item comes back at Stage 3, In progress and Ready, and the next run reads the answer and continues the open steps.
6. If the run fails, leave Status In progress and Stage as they are, set Agent status No action and finish the run as failed with the reason; the founder can select it again.

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
- Stage 4 synthesis is the final specialist in a Stage 3 run. It does not make an item Ready or change a founder decision. Completed at Stage 4 is set by the run; the Specialist deliverable decision it proposes stays **proposed** for the founder.
- Ready selects work; it doesn't authorise anything beyond the stated next step. Only implementation-route items (Feature, Enhancement, Refactor, Fix) are implemented; an investigation-route item never is, whatever its question says.
- An Implementation question is a proposal like any other: never answer it yourself.
- Don't edit the Agent Register.
- Graph Inclusion on the Document Index is the founder's: add new rows with it FALSE and never change it.

## Output requirements

- Dispatch: the items started, their run IDs, run location and session links, and any skipped (claimed, wrong platform) with the reason.
- Item: the specialists used, where outputs were saved, the result of your check, and anything blocked or pending. Implementation route: steps done, branch, commits, pull request, the Stage 1 document and Implementation report links (and the page link if one was requested), and anything left for the founder.
- Status: running, finished (with findings and links), failed or died (with the reason), and waiting on the founder, in that order. Keep it short; offer detail on request.

## Verification before finishing

- Confirm `finish_run` was accepted. Read back any Pipeline cells and Steps rows you wrote and confirm unrelated cells were preserved.
- A proposed decision has a one-line Decision cell and one Options row per option, with one Recommended (see the specialists' linking rules).
- Confirm every specialist skill you named is installed. Report any that aren't.
- Distinguish saved changes from pending work.
