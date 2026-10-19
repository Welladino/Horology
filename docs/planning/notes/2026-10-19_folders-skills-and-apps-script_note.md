# Implementation Note

## Topic
- folders-skills-and-apps-script

## Context
- Follows [the Locations tab note](2026-10-19_pipeline-locations-tab_note.md) from the same day. Its first design (Kind and Output type rows for folders, templates, registers, guides and lists) proved more than needed once the founder reviewed it in the sheet.
- Agents still got rules from Drive guides (Workflow Guide, Presentation Guide) that had drifted from the skills, and skills named the domains in their text.
- The Apps Scripts had the workspace's sheet IDs and ClickUp lists in their code, so a copy of the workbook couldn't be set up without editing source. Pipeline decisions was standalone and ClickUp Sync was bound to the Pipeline, the opposite of what copying the workbook needs.

## Decision
- **Locations holds folders only:** Domain, Entity, Kind (Root folder, Entity folder, Subfolder), Parent (the parent folder's Name, unique within Domain and Entity), Name, Type (Input: the founder's material agents read for context; Output: where agents save; blank: structure), Location and Purpose. Domains with entities go Root folder → Entity folder → Subfolders. Conditional formatting flags duplicates, broken shape and missing links. Output type, the Tree column and the Folder chart tab were removed.
- **Domains tab** (named range `Domains`), built by formula from the Root and Entity folder rows: the only valid Domain and Entity values. **Templates** and **Registers** tabs are maintained by hand.
- **Skills:** a shared `locations.md` (Domains, Input and Output folders, Templates) and `presentation.md` (converted from the Presentation Guide) replace every Drive guide link; no skill names a domain. The supervisor is the default entry point for Pipeline requests unless a skill is named. Codex packages each plugin alone, so each plugin keeps its own copy of the shared references; a unit test keeps the copies identical, links inside their plugin and domain names out of skills.
- **Drive:** guides, registers and templates moved under `05_Horology` (`04_Registers`, `05_Templates`, `99_Archive/03_Guides`); the registers were renamed from Welladino to Horology.
- **Apps Script:** Pipeline decisions is now bound to the Pipeline and reads the Decision Register from the Registers tab, with an Extensions menu. A new bound Locations project draws the folder tree and updates Name and Parent from Drive, using batched Drive API queries (the first version took 47 seconds with one call per folder). ClickUp Sync is standalone, with `PIPELINE_SHEET_ID` and one `LIST_<Domain>` per mirrored domain in Script Properties; list properties are looked up per domain from the Domains tab, keeping the rule against bulk property reads. The old standalone decisions project and the bound ClickUp project were retired.
- Apps Script docs moved from `google_appscript/*/README.md` and `WORKFLOW.md` into [architecture](../../architecture/subscription-agents/apps-script.md) and the [runbook](../../runbook/subscription-agents/clasp.md).

## Rationale
- Templates and registers have their own tabs, so Locations only needs folders, and a parent by name is enough to draw and check the tree; the Locations script keeps names and parents current instead of a hand-maintained ID tree.
- Instructions only in skills removes guide/skill drift; reading domains from the sheet keeps skills usable with anyone's domains.
- Bound core scripts come with a copy of the workbook. ClickUp Sync stays standalone because it is optional and holds a token a copy must not carry. Its state is in the Pipeline's `_ClickUp Sync` tab, so moving projects lost nothing.

## Impact
- Reinstall the rebuilt skill packages for agents to use the new references.
- A new user copies the registers, fills Locations, Templates and Registers, installs the decision triggers from the Extensions menu, and optionally sets ClickUp Sync's Script Properties.

## Follow-Ups
- A people-facing guide in the repo (for example `docs/guide/`), possibly published with GitBook, to replace the archived Drive guides.
- Skills still link the registers directly; they could read them from the Registers tab so only the Pipeline link is configured.
- Delete the retired standalone Pipeline decisions project (`1QyqlFEA…`) from the shared drive.
