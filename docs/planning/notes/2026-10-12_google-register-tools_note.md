# Bounded Google register tools

Date: 2026-10-12

Implemented locally from the existing Welladino workflow plans and verified live register headers. Pipeline and Decision Register use Master; Document Index uses Document Index. IDs and tab identities are fixed in code; callers cannot supply spreadsheets or raw ranges.

- drive_read_pipeline resolves an approved permanent ID and returns a fingerprint.
- drive_update_pipeline permits investigation text, Researching/Awaiting decision and clearing Agent status to No action. Manual items, stale fingerprints, founder decisions/approval, agent selection, stage, target links and scheduling changes are denied.
- drive_index_draft appends an owned draft with a permanent numeric Document ID, sequence and Pipeline association. It leaves graph controls, supersedes and acceptance state unchanged.
- drive_propose_decision appends a question, reason and owned-draft evidence. It leaves Decision, Status, acceptance date, review stage and rework to the founder.

Persistent operation receipts prevent duplicate retries and retain uncertain outcomes for reconciliation. A PostgreSQL advisory transaction lock serializes gateway register writers; it does not serialize human or Apps Script edits. Use a single workflow writer. Values are written literally with userEnteredValue-only field masks and verified by readback; formatting and unrelated cells are preserved. Headers, numeric IDs, bounded row capacity and file ownership are checked before writes.

The example policy assigns no register permissions. Global drive.registers and assignment drive_registers must authorize register names; drive_pipeline_ids must explicitly authorize permanent IDs. Production permission configuration and live write verification remain pending the Google OAuth scope choice. Existing drive.file requires selected-file access to existing registers; spreadsheets scope is an alternative but has broader underlying Google permissions. Gateway restrictions do not narrow the provider token itself.

Verification: 121 local tests passed against disposable migrated PostgreSQL, including 22 register-boundary cases; local HTTP MCP smoke passed authentication rejection, thirty tools and scope denial. External Google register calls were mocked in the write tests. No real register cells were changed, no Cloud Build ran, and no production deployment or migration occurred.

Next: resolve provider authorization, verify narrow writes with isolated fixtures, finalize approved resources, update Agent Register/plugin instructions, verify the actual scheduled runtime and decide run-quota semantics. Build/deploy and local commit remain last.

## Local live verification and scope decision

The operator selected the Sheets OAuth scope with gateway restrictions. The one-time local grant completed and refresh credentials remain in ignored mode-0600 `.env.local`. The provider token has broader underlying Sheets permissions; the gateway fixes the three register identities and permitted fields.

Live local MCP verification used private copies of Pipeline, Document Index and Decision Register plus one owned draft. Original workflow registers were not modified. Pipeline update/replay, draft indexing/replay, proposal/replay, founder-field rejection and out-of-scope Pipeline ID rejection passed. The test exposed two readback representations: native dates return numeric serials and text-table ID columns can return numeric IDs as strings. Corrected both and added regressions. Final full local suite passed 124 cases against disposable Postgres.

Test copies:
- Pipeline: https://docs.google.com/spreadsheets/d/1XHyW09_sOUJeG4sI8SjVIPdRxrLe0jHjT6EaDNv_3VE/edit
- Document Index: https://docs.google.com/spreadsheets/d/14F-JCGQC-UhZds0K_jrkTCTHtdgg-Jw_FSb-yWyEFKw/edit
- Decision Register: https://docs.google.com/spreadsheets/d/1KD0jJV6WzZI1Z86rNo7llTuqM5maO15HWFvyvfivOe8/edit
- Draft evidence: https://docs.google.com/document/d/1W3q8eS6jkbhohFYEOpweVmQRFyg8Rs01mIqcr_t_b0M/edit

The copies retain clearly marked test titles. The test Index contains an extra incomplete diagnostic ID row; it is isolated test data, not a production workflow record. No files were deleted. Agent Register MCP rows 8–13 now distinguish local verification from cloud availability and explicitly retain claim/lease work as pending. Row 21 describes local GitHub writer removal. Plugin source instructions were updated locally; no plugin release was published.

Remaining: finalize production resource/assignment scopes, confirm the actual scheduled runtime, handle identity/run quotas, then Cloud Build/deploy and commit locally. No Cloud Build or production deployment ran in this verification.
