# Decision review web page

The founder wanted to review and choose decision options without adding more Sheets tabs or treating a different choice as rework. Pipeline and Decision Register Master remain the records.

The Pipeline decisions Apps Script now serves a private HTML web page. It lists current proposed decisions and recent outcomes, shows the original question, proposal, reason and evidence, and offers option codes found in the proposal text. The founder can edit final wording, add a reason and approve, park, reject or request rework. The server validates permanent IDs and the current review state, rejects a stale page, saves Status last, then applies only that Pipeline item immediately. The existing timer remains a recovery path.

The page is deployed as version 1 at `AKfycbz3M-ONEZF3ox378oBdoecMb0wV7WdJNZX0jQgrq7NAEDqRZbs0OVCuYPgob7qrPWrr2Q`, with access restricted to the owner. It requires no Cloud Run deployment.

Verification: 18 offline Apps Script tests pass, including alternative choice and stale-review guards; HTML JavaScript syntax and manifest JSON pass checks; `clasp pull` confirms the deployed project contains the page and private manifest. Browser verification was not performed because the founder prohibited browser use without permission. The Apps Script CLI function runner reported `NOT_FOUND` for this web-app deployment, so it did not verify a live page request.
