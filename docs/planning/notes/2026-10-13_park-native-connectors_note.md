# Park GitHub and Google gateway adapters

Date: 2026-10-13

The operator chose to evaluate native GitHub and Google connectors and explicitly postponed Cloud Build while other work remains. Moved adapter sources into `placeholders/connectors/github/` and `placeholders/connectors/google_drive/`. Preserved Google authorization setup, write-receipt helper, unshipped operations migration, connector-specific tests, policy snapshots and a pre-extraction README. Placeholder sources assume their former runtime layout and are not standalone services.

Removed connector imports/registrations and their local policy grants, resource fields and initializer inputs from the active gateway. Retired-tool grants now fail policy startup. The gateway keeps status, Supabase metadata/performance, Firecrawl scraping/Alexandria and Tavily search/extraction: thirteen tools. Google identity OAuth remains; document API authorization is separate and parked. The runtime image contract now asserts that neither adapter nor the Google write helper is packaged.

Retired provider settings were moved to ignored mode-0600 `placeholders/connectors/.env.local`. Active gateway `.env.local` retains Google identity OAuth and active providers. No provider credentials were printed, rotated, revoked or committed. Existing cloud secrets, policy versions and running revisions were not touched.

Updated source plugin instructions and affected Hermes personas to avoid retired gateway tools; native GitHub is usable only when actually configured in that runtime and explicitly authorized for read-only assessment. No native connector was configured automatically, and no plugin release was published.

Historical planning notes retain the earlier implementation state. Current architecture describes the parked sources and the pending native-connector schedule test. Quota windows remain unimplemented; no interval was selected.

Verification: 66 local tests passed; 19 infrastructure-dependent checks skipped. Docker Desktop was unavailable, so disposable-Postgres and full HTTP smoke checks could not run. Alembic reports the active head as 20261011_002, preserving the deployed OAuth/quota migration chain. Retired provider settings are confirmed Git-ignored; diff whitespace checks passed. Cloud Build, deployment, schedule creation and commit remain deferred.
