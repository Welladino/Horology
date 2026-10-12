# Remove descriptive spreadsheet access IDs

Removed `disabled_access_ids` from the example, local, expansion-local and historical cloud policy files, and from `gateway_status`. The field was descriptive only and had drifted between policy snapshots. Named JSON tool allowlists and provider/resource checks remain the authority for access; all other policy values are preserved.

Cloud Run still reads its existing Secret Manager policy. Local file edits do not change deployed configuration. No Cloud Build, deployment or commit performed.
