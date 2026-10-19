# Implementation Note

## Topic
- pipeline-locations-tab

## Context
- Branch `version_v1.2` (commit `a584acc`) grew `google_appscript/pipeline-decisions` into a `workspace` Apps Script project: a web setup page, a folder layout that created Drive folders, register setup and settings. It was more than the workflow needs.
- Destinations lived in the Agent Location Directory, a Google Doc mixing shared records, templates and per-domain folders in prose and tables, which the founder could not easily reshape.

## Decision
- Drop the `workspace` project. Keep `google_appscript/pipeline-decisions` as it is on `main`, the only Apps Script logic besides the optional ClickUp sync.
- Move the Agent Location Directory into a `Locations` tab in the Welladino — Pipeline workbook: one row per destination with Domain, Entity, Kind (Folder, Template, Register, Guide, Task list, Repository), Destination, Location and Use. Welladino rows are shared by every domain. The founder decides the folder structure by editing rows; nothing creates folders automatically.
- Skills and docs now point at the tab (`#gid=2040100904`) instead of the Doc.

## Rationale
- A sheet row per destination is easy to filter, add to and read by header, and sits next to the Pipeline items that use it. Creating folders from code was the part that was overdone; choosing them is a founder decision.

## Impact
- All skills that read destinations or templates now read the Locations tab. Rebuild and reinstall the skill distributions for the change to reach agents.
- The Pipeline Read Me has a Locations row.

## Follow-Ups
- Fill the blank Location cells for `00_Guides`, `01_Registers` and `99_Archive` (the Doc gave no links for them).
- Archive the old Agent Location Directory Doc to `99_Archive` once agents use the tab.
