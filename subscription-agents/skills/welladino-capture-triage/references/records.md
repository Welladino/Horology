# Pipeline records

Read live Master headers and resolve fields by name; never assume column offsets. Domain tabs are filtered views, not editable records.

[Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit) owns work selection, scope, stage and status. Its permanent numeric ID is independent of External ID, which can contain an optional historical ClickUp identifier. ClickUp Pipeline URL identifies the associated task. Document count is derived from Document Index, not a list of links. Current decision ID identifies the active Decision Register record.

Use Title, Domain, Entity, Type, Summary / Why, Next step / Research question, and Revisit trigger for capture. Entity is blank for Welladino, Article Aggregator and Horology, and names a specific Newsletter or Ecommerce business when applicable. Preserve Created; update Updated for substantive edits with the actual date.

Read the live status dropdown before writing. Inbox captures new work; Park/Parked defers it; Researching indicates an authorised investigation; Awaiting decision requests founder review; Approved authorises the specified next-stage deliverable; Hand off/Handed off records handoff; Reject/Rejected retains rejected work. Match the sheet's actual spelling. Stage and Review stage disambiguate investigation, decision and specialist review; follow the Workflow Guide and existing values.

Agent status is No action or Ready. Agent type includes Manual, Unassigned, ChatGPT, ChatGPT Work, Codex, Claude Code, Claude Cowork and Horology; verify live selections. Manual is founder-led and skipped by scheduled agents. Default new captures to No action and Unassigned unless instructed otherwise. Ready selects work; it does not launch a run or authorise implementation.

Link type, URL and GitHub branch identify the work target. Verify repo remote and branch before inspecting code. Supporting documents belong in Document Index. Do not recreate removed Research / Plan links, Decision link or ClickUp execution link columns.

Allocate permanent numeric IDs from live records; never renumber or reuse IDs. There is no concurrent-agent allocator: use one writer and reread before saving; a coordinated allocator is required before enabling parallel writers. Use Pipeline ID in metadata because sheet row URLs move. Upsert by identity, preserve unrelated cells and inspect ambiguous failures before retrying.
