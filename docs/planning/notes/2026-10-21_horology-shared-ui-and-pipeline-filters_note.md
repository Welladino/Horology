# Shared Apps Script UI and Pipeline filters

The founder asked for the two bound Apps Script projects to share basic UI components, for the Decisions list to use rows only, and for Pipeline browsing to have filters. The Decisions and Pipeline rows had different spacing and the native accordion arrow was visibly off centre.

`google_appscript/shared-ui/` now owns the common theme, button/input/pill/row styles and a text-only DOM helper. Its build script generates `SharedUi.html` in each independent Apps Script project; the pages include their local copy. Decisions uses one shared row structure with an explicit centred chevron. Pipeline rows use the same structure, while Pipeline cards remain available. Search combines with Domain and Status filters; More filters includes Entity, Type, Agent status, Agent type, Run location and Stage. Entity choices follow Domain. Review stage was omitted because it is represented in Decisions.

Both projects check that their generated fragments match the shared source before running their existing offline tests. The workspace tests also cover decision grouping and combined Pipeline filtering. No Sheets schema or Cloud Run change is needed. Browser inspection requires the founder's permission and was not performed.

Both bound Apps Script projects were pushed. The existing Horology workspace deployment was updated to version 5 at the same URL, confirmed by `clasp deployments`. The main checkout remains uncommitted; no PR was created.
