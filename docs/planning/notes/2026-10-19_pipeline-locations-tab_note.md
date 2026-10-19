# Implementation Note

## Topic
- pipeline-locations-tab

## Context
- Branch `version_v1.2` (commit `a584acc`) grew `google_appscript/pipeline-decisions` into a `workspace` Apps Script project: a web setup page, a folder layout that created Drive folders, register setup and settings. It was more than the workflow needs.
- Destinations lived in the Agent Location Directory, a Google Doc mixing shared records, templates and per-domain folders in prose and tables, which the founder could not easily reshape.

## Decision
- Drop the `workspace` project. Keep `google_appscript/pipeline-decisions` as it is on `main`, the only Apps Script logic besides the optional ClickUp sync.
- Move the Agent Location Directory into a `Locations` tab in the Welladino — Pipeline workbook: one row per destination with Domain, Entity, Kind (Folder, Template, Register, Guide, Task list, Repository), Output type, Location and Use. Welladino rows are shared by every domain. The founder decides the folder structure by editing rows; nothing creates folders automatically.
- Agents look a row up by Domain + Entity + Kind + Output type and use the Drive ID in Location, never a path or folder name. No match, several matches or a blank Location means ask the founder. The digest is the one exception: without a Digests row it uses the Horology Root folder and says so.
- The sheet enforces it: Output type is a dropdown, Folder rows only accept Drive folder URLs, duplicate keys turn red and blank Locations yellow.
- Skills and docs now point at the tab (`#gid=2040100904`) instead of the Doc.

## Rationale
- A second suggestion was a two-tab model, a Locations tree with Parent IDs plus a Destinations mapping. It was not adopted: Drive already holds the folder tree, so a copy in the sheet would drift when folders move, and agents need only one folder ID per purpose. Domain + Entity already tell same-named folders apart, and a shared folder is just the same URL on two rows. Revisit if agents ever have to create folders under a known parent.
- A sheet row per destination is easy to filter, add to and read by header, and sits next to the Pipeline items that use it. Creating folders from code was the part that was overdone; choosing them is a founder decision.

## Impact
- All skills that read destinations or templates now read the Locations tab. Rebuild and reinstall the skill distributions for the change to reach agents.
- The Pipeline Read Me has a Locations row.

## Follow-Ups
- Fill the blank Location cells for the Welladino Guides, Registers and Archive folders (the Doc gave no links for them).
- Archive the old Agent Location Directory Doc to `99_Archive` once agents use the tab.
