# Horology workspace item editing and grouped decisions

The founder wanted the Pipeline card/row control aligned with Decisions, Pipeline item editing, and one expandable decision entry per Pipeline item. Domain and Entity stay fixed after capture; Stage remains controlled by workflow transitions.

The Pipeline view now keeps its layout control beside the heading and its search field below. An item's edit form changes its descriptive fields, Type and agent assignment. It rejects stale views and disallowed Agent status moves, and selects Stage 1 automatically when an Inbox item moves from Stage 0 to Ready. Domain, Entity, Status and Stage are shown read-only. Decisions are grouped by Pipeline ID, with each underlying decision retaining its own detail page and Decision Register row.

Offline Apps Script tests cover valid and invalid item edits. The web page script passes a syntax check. Browser inspection was not performed because the founder requires permission before browser use. No Sheets tab or Cloud Run change is involved.

The existing web app deployment was updated to version 4 at the same URL. `clasp deployments` confirmed the version. The main checkout remains uncommitted; no PR was created.
