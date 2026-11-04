# Web item page: numbered steps and quick edit of agent fields

## Context

Pipeline item 65 (ClickUp HOR-15). On the web app's item page, long cells split step numbers from their text: item 39's Next step showed "1." on its own line, then "Reader demand: …" as the next paragraph. Changing Agent status, Agent type or Run location needed **Edit item**, and Domain and Entity could not be changed from the web app at all.

## Cause

`paragraphChunks` in `google_appscript/pipeline-decisions/src/Review.html` splits a line into sentences at a full stop followed by a capital, and starts a new paragraph at a labelled sentence ("Check:", "After the decision:"). A step marker such as `1.` counts as a sentence, so when the step text opens with a labelled phrase the marker is left as a paragraph of its own. Item 55's earlier numbered Next step ("Map the current rules:", "After the decision:", "Check:") had the same shape. The board cards and Steps lists had no overflow rule, so a long unbroken token (a file path) could widen them at phone width.

## What changed

- **Rendering.** A line that starts with `1.`, `1)` or a bullet stays one paragraph with its marker, shown with a hanging indent. Plain prose, labelled sentences and the 260-character chunking are unchanged. Card titles and step lists wrap long tokens.
- **Quick edit.** The item page has an **Agent and domain** section: Agent status (only the allowed moves), Agent type, Run location, Domain and Entity (following the chosen Domain), with **Save agent and domain**. A stale save shows the conflict and reloads the item. **Edit item** keeps Title, Type, Summary / Why, Next step and Revisit trigger, and shows the five fields read-only.
- **Server.** `updatePipelineItemFromWeb` accepts Domain and Entity. A changed Domain must be on the Domains tab; Entity must be one of its entities, or is cleared when the domain lists none. Unchanged older values are left alone. The script lock, version check, Agent status moves and Ready requirements are unchanged. Changing Domain does not move documents already in Drive.

## Verification

- `npm test` in `google_appscript/pipeline-decisions`: new cases for items 39 and 55 text, Domain and Entity changes (valid, unknown domain, entity of another domain, cleared entity, stale version, disallowed status move, unchanged legacy domain) and the item page's Agent status choices.
- `.venv/bin/python -m pytest tests/unit -q`.
- `npm run clasp:push` was run on 03/11/2026 after checking that the live project matched the branch base (`clasp pull` diff empty), so the project's HEAD code has this change. The web-app deployment was **not** updated: the live `/exec` page still serves version 25 until the founder deploys a new version.

## Founder steps

1. Apps Script editor for the Pipeline decisions project: **Deploy → Manage deployments**, the existing web-app deployment, **Edit**, Version **New version**, **Deploy** (or `clasp deploy --deploymentId <existing ID>` from `google_appscript/pipeline-decisions`).
2. Open items 39 and 55 in the workspace and run the checks in the runbook's "Deploy the web page after a change".
