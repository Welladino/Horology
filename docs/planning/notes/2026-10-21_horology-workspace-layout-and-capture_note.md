# Horology workspace layout and item capture

The founder asked for the private Apps Script page to show decisions as either cards or rows, reveal inputs and options when one is opened, and handle Pipeline capture from the same URL. The old Add Pipeline item Extensions menu entry was removed, while the Pipeline decisions menu now links to the page.

The web app keeps Decision Register and Pipeline Master as records. It uses the former item form's domain, dropdown and Ready validation rules. New items receive the next permanent ID under a script lock and start in Inbox/Stage 0, or Stage 1 when marked Ready. The decision list now opens a focused detail view with option cards and a collapsed full proposal.

Deployment `AKfycbz3M-ONEZF3ox378oBdoecMb0wV7WdJNZX0jQgrq7NAEDqRZbs0OVCuYPgob7qrPWrr2Q` was updated to version 2, preserving its URL. Both bound Apps Script projects were pushed; no Cloud Run deployment, Sheets tab, commit or PR was created.

Verification: Pipeline decisions tests pass (20), including item creation and invalid Ready input. Workbook project tests pass (22). The web page JavaScript passes syntax checks. The founder had already confirmed the first-version URL worked; browser inspection of this version was not performed because browser use requires the founder's permission.
