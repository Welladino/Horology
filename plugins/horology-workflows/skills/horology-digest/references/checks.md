# What to check

## Report card (Pipeline Master)

- Count items by Status, by Agent status (No action, Plan, Ready) and by Agent type, plus per Domain.
- Ready items by Agent type and Run location, so the founder knows which sessions to start.

## Done since the last digest

- Runs rows with Finished in the period: Pipeline ID, Skills used, Status, Output document IDs, Notes.
- Document Index rows created or revised in the period, including ones without a matching run.
- Decision Register rows recorded in the period, with their status.
- For each finished item, the key finding and recommendation from its output documents.

## Waiting on the founder

- Pipeline items with Status Awaiting decision, oldest first, with days waiting (from Updated).
- Decision Register rows with status proposed.
- Items with Agent status Plan.
- Rows that look too big for one run (several unrelated questions in Next step, or a broad scope with no question). List them as "set Plan if you agree"; don't change them.

## Health checks

| Check | How |
|---|---|
| Stale claims | Runs rows with status claimed or running and Claim expires in the past |
| Failed runs | Runs rows with status failed in the period, with their notes |
| Stuck decisions | Awaiting decision for more than 7 days |
| Missing records | Output document IDs in Runs that aren't in the Document Index, or Awaiting decision items with no output documents |
| Steps left open | Steps rows still proposed for items that are no longer Ready |
| Near-duplicates | Documents written in the period whose `auto_link_similar_documents` or `get_related_documents` links show a similarity of 0.90 or more |
| Contradictions | New recommendations that conflict with an accepted decision on the same subject |

## Graph checks (Document Index and document graph)

- Graph Sync Status `not_shared`, `too_long` or `error`, with the fix (share the folder, split the file, check the type).
- Graph Inclusion TRUE rows not yet `synced`.
- New finished deliverables with Graph Inclusion FALSE that look worth including (suggest only; the founder decides).
- `list_unembedded_documents` is empty; if not, list the documents.
