# Completed status and ClickUp comments

## Context

The founder wants to close ClickUp tasks manually after accepting the final Horology deliverable, while retaining milestone comments on linked tasks.

## Decision

- Rename the final Pipeline status from **Handed off** to **Completed**.
- Keep one-way status mapping for the other canonical Pipeline statuses. **Completed** sends no ClickUp status update.
- Keep the hourly sync and its change-based comment behavior. Start comments with **Horology updates:** and include the workspace and Pipeline row links.
- Show the exact proposed comment in `previewSync`; the first sync remains a baseline with no historical comment.

## Verification

The ClickUp and Pipeline Apps Script tests and workflow unit tests passed. Both Apps Script projects were pushed; the existing workspace deployment URL was updated to version 18. The Pipeline Read Me, conditional formatting and live Workflow Guide were updated. No live ClickUp comment was posted for this change.
