# Planning deliverables in Drive and removal of the GitHub writer

Date: 2026-10-12

## Decision

The operator selected Google APIs for Drive/Docs/Sheets access and will enable those APIs using the protected administrator. Planning deliverables will be draft Google Docs in the appropriate domain planning folder, resolved from the Location Directory. Research/assessment sessions retain read-only GitHub access; no repository-writing tool is needed.

The operator chose shared access to currently approved tools for the initial scheduled agents. Separate agent profiles/services are deferred. Existing resource boundaries and paid-provider budgets remain enforced; unattended OAuth and repeat-run quota behavior still need verification.

## Changes

Removed the github_create_planning_note registration, writer module, write-policy fields and optional write-token references. Restored the shared provider transport to HTTP 200 responses only. Native smoke now requires 24 tools and verifies a call to the removed writer is rejected as unknown. Historical notes retain the previous disabled implementation state; current documentation describes removal.

Google adapters are unchanged in this removal. API enablement alone does not authorize Drive access: provider OAuth, restricted draft creation/editing, register field rules and live verification remain to implement. Do not report Google writes as available before those are tested.

## API enablement identity

Use gcp-deployment@welladino.com in the Console for project horology-dev. The daily account is a viewer; horology-deployer deliberately lacks serviceusage.services.enable. The horology-admin local gcloud configuration selects the protected administrator without deployer impersonation. No IAM broadening is needed.

Enable drive.googleapis.com, sheets.googleapis.com and docs.googleapis.com. API activation belongs to the operator; no API was enabled by this change.

### Local Google verification — 2026-10-12

Google provider authorization completed using the localhost callback. Refresh credentials are stored only in ignored `.env.local`, with mode 0600. No production deployment was performed.

The authenticated local MCP test passed: existing Google Doc read, exact approved Agent Register Sheet range read, one draft created in Horology's Plans folder, revision-controlled edit, subsequent content read, repeated creation returning the same document, and rejection of edits to an existing guide. This used a disposable local PostgreSQL database, including the new operations-receipt migration; production migrations have not run. The existing automated suite passed 83 tests.

Test draft: https://docs.google.com/document/d/1uWzipoixACe9Jg2-oJ4shhFzS1YAlb83raNddUgV0LU/edit

Remaining before release: dedicated automated coverage of Google refresh and draft receipts, template-copy verification, final production assignment scopes, secret provisioning and migration/deployment. Actual scheduled-runtime unattended access and identity/run-quota separation remain deferred. The local test proves refresh-based API access without another interactive login; it does not verify a scheduled AI-platform run.

### Additional local regressions — 2026-10-12

Added 16 Google regression cases covering concurrent refresh caching, expiry, revoked/malformed token responses, timeouts, template-copy destination/tags, scope denial, moved/trashed/cross-assignment/non-draft documents, stale revisions, durable receipt replay, conflicting payloads, assignment isolation and concurrent claims. Full local suite excluding Docker-stack tests passed 99 cases against disposable migrated PostgreSQL.

Live template verification remains incomplete: the current ignored environment no longer supplies GOOGLE_DRIVE_CLIENT_ID, so authorization fails before reading or copying a template. No draft was created by these failed attempts. Restore provider credentials or repeat the local authorization before retrying. Bounded register-write tools still need implementation and verification. No Cloud Build, production migration or deployment was performed.

### Provider configuration and live template check — 2026-10-12

Resolved the local credential-name mismatch: the existing client used GOOGLE_OAUTH_CLIENT_ID/SECRET, while the provider loader expects GOOGLE_DRIVE_CLIENT_ID/SECRET. Restored those aliases from the existing private values without changing OAuth clients or repeating consent.

Live local MCP template-copy verification passed with the approved Plan template and Horology Plans destination: copy, read, revision-controlled edit, content readback, idempotent replay and existing-guide edit denial. Test document: https://docs.google.com/document/d/1-mpwigopYPjGYmcy7rvhZhsTU6_2t1y-A_AnRHg3RFQ/edit

The test client's default five-second HTTP timeout expired after the copy had completed. The durable completed receipt preserved the result; retrying the same operation key with a 45-second test-client timeout returned the existing document rather than creating another copy. Runtime provider timeout settings were not changed. Full local regression suite passed 99 tests. This illustrates why actual scheduled-platform timeout behavior still needs verification.
