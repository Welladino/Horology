# Records and linking

Read live headers and dropdowns before writing. Edit Pipeline and Decision Register Master only; domain tabs are filtered views. Resolve items by permanent IDs, not row positions.

- [Pipeline](https://docs.google.com/spreadsheets/d/1aL678ACs97YpLIGrGU5LbpXHc7jQBxl64ED-sLyehvI/edit): permanent numeric ID; optional External ID; domain/entity, title, scope, status, Stage and Review stage. Current decision ID selects the active decision; ClickUp Pipeline URL identifies its UI task; Document count is derived from the Index. Removed link columns must not be recreated. Agent type Manual is skipped by scheduled agents; Ready is selection, not execution permission.
- [Document Index](https://docs.google.com/spreadsheets/d/1kObhQNjsFhziS-wRzjaEIzr9j8jjbfvd-ZgvzuwQ-Jc/edit): upsert by Drive file ID/URL, preserving permanent numeric Document ID. Associate each document with Pipeline ID, Pipeline title and Related Pipeline URL where those live fields exist. Use the revision/sequence field and Supersedes document ID for substantive replacements; retain originals. An original plan and an assessment may both belong to one Pipeline item without either superseding the other. Copy exact field names and dropdown values from the live sheet.
- [Decision Register](https://docs.google.com/spreadsheets/d/1_megp_hD4gwRuF4wmk4g2vQGAWbLl4uNUpho-oLoygE/edit): permanent numeric Decision ID, Pipeline ID/title, evidence links, affected plan, reason, decision/status, Review stage and Rework instructions. Multiple decisions can refer to one Pipeline item. Only explicit founder choices are accepted decisions. Proposed decisions have no invented acceptance date. Preserve history and supersedes references.

Allocate independent numeric IDs within each register; never renumber or reuse IDs. Use a single writer and reread before saving; concurrent allocation is not implemented. External IDs and Drive file IDs remain separate identifiers.

Metadata carries domain, entity, Pipeline ID/link, purpose, draft status and related decision when applicable. Entity is blank for Welladino and Article Aggregator. Templates and destinations are resolved from the Location Directory. Copy templates; preserve originals. Use native headings, lists and tables according to the Presentation Guide.

No graph importer is configured. Never claim graph synchronization merely because a document is indexed. Verify live graph inclusion/sync selections before setting them. Platform skills, Drive access and scheduling must each be configured separately.
