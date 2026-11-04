# What to check

## Report card (Pipeline Master)

- Count items by Status, by Agent status (No action, Plan, Ready) and by Agent type, plus per Domain.
- Ready items by Agent type and Run location, so the founder knows which sessions to start.
- Items In progress (implementation route), with their Stage and how many Steps rows are Done of the total. Finished implementations link their Implementation report and Stage 4 page under Done since the last digest.

## Done since the last digest

- `list_runs` for the period (`since_hours`): Pipeline ID, kind, status, skills used, steps done, outputs and notes. Skills, steps and notes are self-reported; outputs and status changes come from the sheets.
- Document Index rows created or revised in the period, including ones without a matching run.
- Decision Register rows recorded in the period, with their status.
- For each finished item, the key finding and recommendation from its output documents.

## Waiting on the founder

- Pipeline items with Status Awaiting decision, oldest first, with days waiting (from Updated) and Review stage (an Implementation question holds up a half-done implementation).
- Decision Register rows with status proposed. A proposed Specialist deliverable decision on a Completed Stage 4 item is a finished deliverable to look at, not a blocked item.
- Items with Agent status Plan.
- Rows that look too big for one run (several unrelated questions in Next step, or a broad scope with no question). List them as "set Plan if you agree"; don't change them.

## Health checks

| Check | How |
|---|---|
| Stale claims | `list_runs` entries with status claimed or running and `expired` true |
| Failed runs | `list_runs` entries with status failed in the period, with their notes |
| Stuck decisions | Awaiting decision for more than 7 days |
| Missing records | Investigation-route runs finished as done with no outputs, or Awaiting decision items with no output documents (an Implementation question needs only its Decision row); Completed Stage 4 items reached after 03/11/2026 whose Current decision ID is not a Specialist deliverable decision; implementation-route items Completed after 04/11/2026 with no Implementation report or Stage 4 page in the Document Index, or still at Stage 3; items started after 04/11/2026 with no Stage 1 document; implementation-route runs finished as done with no branch, commit or pull request in their notes |
| Stalled implementation | In progress items with Agent status No action and no live claim: the run failed or stopped; the founder can select them again |
| Wrong route | Investigation-route Types (Idea, Research, Direction, Plan) In progress, or implementation-route Types (Feature, Enhancement, Refactor, Fix) Researching or at Stage 2 after 29/10/2026, or at Stage 4 with a Status other than Completed, Parked or Rejected; older items may still be on the investigation route |
| Unfinished steps | Completed items with Steps rows still Planned |
| Unexpected moves | `get_item_history` changes marked `expected: false` for items that changed in the period |
| Near-duplicates | Documents written in the period whose `auto_link_similar_documents` or `get_related_documents` links show a similarity of 0.90 or more |
| Contradictions | New recommendations that conflict with an accepted decision on the same subject |

## Graph checks (Document Index and document graph)

- Graph Sync Status `not_shared`, `too_long` or `error`, with the fix (share the folder, split the file, check the type).
- Graph Inclusion TRUE rows not yet `synced`.
- New finished deliverables with Graph Inclusion FALSE that look worth including (suggest only; the founder decides).
- `list_unembedded_documents` is empty; if not, list the documents.
