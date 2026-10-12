# Shared daily/monthly paid-provider budgets only

Date: 2026-10-13

The operator withdrew session-based caps and chose only shared daily/monthly spending limits per paid provider. Removed per-tool counts, per-assignment credit caps and per-provider assignment call caps from the active ledger, local/example policies and consent presentation. No session IDs, hooks, quota-window rollover or run provisioning are needed for this budget model.

Firecrawl and Tavily remain separately capped at 50 credits per UTC day and 500 per UTC calendar month. Reservations remain atomic through the existing coordinator row lock and use database time. Existing history/cache persists unchanged; there is no quota reset, refund, new schema or migration. Tool/resource authorization and request/output bounds remain. JSON owns permission rules; spreadsheet IDs remain documentation.

Updated active documentation and plugin source, and revised regression tests to permit more than two paid calls while retaining combined daily/monthly exhaustion checks. Local mocked tests passed; database-backed tests still require Docker/disposable Postgres. No paid calls, Cloud Build, deployment or commit performed.

Assignment authorization expiry is unchanged in this change. It was introduced as a temporary-access cutoff, not an OAuth requirement. Ongoing agents can use a separately approved persistent/revocable permission profile; OAuth handles access/refresh token renewal but does not override server-side authorization expiry.
