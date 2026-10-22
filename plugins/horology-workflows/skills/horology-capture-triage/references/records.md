# Pipeline records

Read live Master headers and resolve fields by name; never assume column offsets. Use the Master table's filters to view one domain.

[Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit) owns work selection, scope, stage and status. Its permanent numeric ID is independent of External ID, which can contain an optional historical ClickUp identifier. ClickUp Pipeline URL identifies the associated task. Document count is derived from Document Index, not a list of links. Current decision ID identifies the active Decision Register record.

Use Title, Domain, Entity, Type, Summary / Why, Next step / Research question, and Revisit trigger for capture. Domain and Entity must be values from the Domains tab; Entity is set only for a domain that lists entities ([domains, folders and templates](locations.md)). Preserve Created; update Updated for substantive edits with the actual date.

Write readable text in Summary / Why, Next step / Research question and Revisit trigger. Keep a single short thought on one line; put distinct points on separate lines, with a blank line between paragraphs when useful. Number ordered steps, one step per line. Save actual line breaks in the cell value, not the literal characters `\n`, and do not compress a list into one long sentence. Preserve the founder's line breaks when editing existing text. Read back multiline values to confirm the breaks survived.

Read the live status dropdown before writing. Inbox captures new work; Parked defers it; Researching indicates an authorised investigation; Awaiting decision requests founder review; Approved authorises the specified next-stage deliverable; Completed records accepted Stage 4 work; Rejected retains rejected work. Match the sheet's actual spelling. Stage identifies the current step; Review stage identifies the proposal or deliverable under review. Stage 1 work moves to Stage 2 for review. After Stage 3 work is saved, the supervisor makes the Stage 4 visual synthesis in the same run and then presents both outputs for review. Follow [workflow.yaml](workflow.yaml) and existing values.

Agent status is No action, Plan or Ready. Plan asks the planner to scope or split the item; the planner sets it back to No action when done. Ready selects the item for the platform named in Agent type; it does not launch a run or authorise implementation. Runs start when the founder asks a supervisor session to run Ready items.

Agent type is Claude Code, Codex, Manual or Unassigned; verify live selections. Each platform runs only its own rows. Manual is founder-led and never run by agents. Run location is Local or Cloud (blank means Local) and decides where the item's session runs. Planner output is Yes when the planner has written a sharper question or steps for the row; only the planner sets it. Default new captures to No action and Unassigned, with Run location blank, unless instructed otherwise.

Runs are recorded in the execution history through the document-graph connector (`claim_item`, `finish_run`), not in the workbook; the planner writes steps as a numbered list in Next step. The rules are in the supervisor skill's runs reference.

Link type, URL and GitHub branch identify the work target. Verify repo remote and branch before inspecting code. Supporting documents belong in Document Index. Do not recreate removed Research / Plan links, Decision link or ClickUp execution link columns.

Allocate permanent numeric IDs from live records; never renumber or reuse IDs. There is no concurrent-agent allocator: use one writer and reread before saving; a coordinated allocator is required before enabling parallel writers. Use Pipeline ID in metadata because sheet row URLs move. Upsert by identity, preserve unrelated cells and inspect ambiguous failures before retrying.

The allowed status and Agent status moves, and who may make each, are defined in [workflow.yaml](workflow.yaml). Follow it; a move not listed there is unexpected.
