# MCP deployment plan for GCP

## Topic
- gcp-mcp-deployment-plan

## Context
- Deploy the restricted gateway and document graph from Horology, using direct gcloud commands and the local gcloud MCP. This note records the agreed plan and tracks pending work; it does not claim implementation or deployment.
- Verified through the GCP MCP: project display name `horology`, project ID `horology-dev`, active deployment account `gcp-deployment@welladino.com`, billing enabled on `Welladino - Default payments`.

## Decision
- Region: `us-central1` (Iowa), replacing the earlier Singapore and South Carolina proposals.
- Use the existing Neon database for durable gateway quota accounting, with dedicated gateway tables. Do not provision Firestore or Terraform.
- Keep `mcp-gateway` and `document-graph` as separate Cloud Run services, both packaging the root shared runtime. Keep the public Supabase CA in the gateway image.
- Keep the setup proportionate to personal use: authenticated services, protected credentials, durable quotas, bounded scaling and useful logs.

## Rationale
- Reuse the existing Postgres infrastructure and transactional accounting rather than introduce another database service. Actual Neon capacity and region remain to be checked.
- `us-central1` is a Cloud Run Tier 1 region and the pricing basis for its free-tier discount. The free allowance is not exclusive to Iowa. Cloud Run free-tier usage is shared across projects on the billing account; this project does not get an independent allowance. Choosing this region does not guarantee a zero bill. Image storage, builds, secrets, networking and Neon have separate usage/pricing.
- Source checked 2026-10-11: https://cloud.google.com/run/pricing

## Impact
- Neon accounting is implemented and verified; the local gateway uses it too. Existing architecture docs continue to describe the implemented system.
- Preserve per-provider limits: 50 credits per UTC day, 500 per calendar month, two paid upstream requests per assignment/provider, and existing per-tool invocation limits. Reservations remain charged after ambiguous/failed upstream calls; no automatic retries.
- Cloud Run local files are temporary; quota state must survive instance replacement. Source: https://docs.cloud.google.com/run/docs/container-contract#file_system
- Google Drive OAuth and scheduled-agent client compatibility remain pending. Successful cloud deployment alone does not prove scheduled subscription-agent access.

## Follow-Ups
Complete in this order; tick only after verification.

### 1. Persistent gateway accounting
- [x] Confirm the existing Neon database/branch and region without copying credentials into documentation.
- [x] Design dedicated tables for budgets, assignment/tool usage and any persistent cache needed by the existing ledger contract; determine whether one table is sufficient.
- [x] Prepare reviewed schema SQL and a gateway credential limited to these tables. Keep document-graph data access separate.
- [x] Implement transactional reservations safe across concurrent requests/instances. Fail closed on accounting connection failures. Reuse shared timeout/error/logging settings.
- [x] Decide how to retain existing spending history during cutover; do not silently reset quotas.
- [x] Test UTC daily/monthly boundaries, assignment expiry, concurrency, failure behavior and persistence across restarts.
- [x] Apply the reviewed schema and verify against Neon before enabling paid cloud tools.

### 2. Cloud-ready services
- [x] Configure PORT and externally correct gateway issuer/resource URLs; retain local defaults.
- [ ] Provide a cloud policy configuration and assignment provisioning/expiry process.
- [x] Build Linux amd64 images from the repository root, including shared-runtime and the gateway CA, excluding local env/client files.
- [x] Run the required local tests and transport smoke checks.

### 3. Credentials and authentication
- [x] Put gateway provider credentials, quota DB credentials, document-graph Neon credentials and OpenRouter key in Secret Manager; never print secret values.
- [x] Create a runtime identity for each service with access to its required secrets.
- [x] Require authentication for both services. Test the gateway using a compatible authenticated MCP client first.
- [x] Implement Google-backed MCP OAuth; native client login and external ingress approval remain pending. Google Drive provider OAuth is a separate follow-up.
- [x] Retain existing integration resource allowlists and quota enforcement.

### 4. Build and deployment
- [x] Prepare reproducible gcloud commands/runbook with explicit `horology-dev` and `us-central1`; no Terraform.
- [x] Verify required API availability and report any missing prerequisites.
- [x] Create Artifact Registry, publish tested images and deploy separate Cloud Run services.
- [ ] Start with request-based billing, minimum instances zero and a low maximum instance count; validate MCP session behavior under instance replacement/scaling.
- [x] Configure secret/policy injection and verify deployed revision settings.
- [ ] Review billing alerts and image/log retention. Budget alerts notify; they do not cap spending. Choose an alert amount with the operator.

### 5. Cloud verification
- [x] Confirm unauthenticated calls are rejected and authenticated tool discovery works.
- [ ] Confirm repository/schema restrictions, auth-schema exclusion and denied tools.
- [ ] Confirm quota state survives revision replacement and cannot be bypassed by parallel calls.
- [ ] Verify timeout/connection failures produce safe errors and usable structured logs.
- [ ] Make minimal live checks for GitHub, Supabase, Tavily and Firecrawl within approved budgets; keep Google disabled until configured.
- [ ] Verify document-graph authentication and bounded embedding usage before cloud writes.
- [x] Record endpoints, revisions, validation and rollback commands without secrets.

### 6. Client and schedule rollout
- [ ] Verify each intended Codex/Claude/ChatGPT scheduled client can connect and authenticate; record actual supported behavior.
- [ ] Implement per-run assignment/credential provisioning and tool isolation.
- [ ] Complete Google provider OAuth and scoped Drive access.
- [ ] Create schedules only once client access, credentials and quota lifecycle work.

## Current status
- Initial private Cloud Run deployment, Secret Manager and runtime identities are verified. See [deployment evidence](2026-10-11_cloud-run-mcp-deployment_note.md). Client OAuth is implemented; native browser verification, external ingress approval, automated assignment provisioning, schedules, live provider cloud checks and billing alerts remain pending.
- This note supplements [the earlier security follow-up](2026-10-11_gateway-security-follow-up_note.md).


## OAuth implementation update (2026-10-11)

- [x] Google OIDC identity verification and explicit MCP client consent implemented.
- [x] SDK OAuth discovery, DCR, PKCE, code/refresh/revoke endpoints implemented.
- [x] Neon OAuth schema migration applied; grant rotation/revocation atomic; assignment quotas preserved.
- [x] Google client credentials in service-specific versioned Secret Manager secrets.
- [x] OAuth revision mcp-gateway-00004-25t deployed privately and verified; 76 tests pass.
- [x] OAuth request-query logging exclusion configured.
- [x] Explicit approval and service-level public ingress enabled via disabled gateway invoker IAM check; OAuth remains required for tools.
- [ ] Native Codex Google browser login and authenticated tool verification.
- [ ] Separate per-scheduled-run assignment provisioning and client configuration.

See [OAuth note](2026-10-11_gateway-oauth_note.md) for details. Document graph and Drive access remain separate.

## Release pipeline follow-up (2026-10-12)

See [Cloud Build and consent work](2026-10-12_cloud-build-consent_note.md) and [release runbook](../../runbook/gcp/cloud_build.md). Cloud Build runs in us-central1 with a dedicated build identity. Artifact Registry cleanup keeps five recent versions per package plus protected deployed images. Unattended-access testing and separating identity from per-run quotas remain deferred.

### Verified release update

- [x] Cloud Build in us-central1: tests, dependency audits, source/image scans and runtime image checks passed; both images published and deployed by digest.
- [x] Improved consent presentation deployed; existing Codex OAuth connection still works.
- [x] Artifact Registry retention activated, deployed digests protected, obsolete local release tags removed.
- [ ] Unattended-access testing in the selected scheduled runtime (deferred).
- [ ] Separate login identity from per-run assignments and quotas (deferred).

Evidence and unfixed image findings are recorded in the [2026-10-12 implementation note](2026-10-12_cloud-build-consent_note.md).

## Horology routine deployment access (2026-10-12)

- [x] Direct daily-user impersonation of a project-specific restricted deployer, scoped resource grants, and separate CLI viewer/admin profiles.
- [x] Real Cloud Build submission passed; both services passed deployment validation without a live revision change.
- [ ] Folder-wide developer visibility/project provisioning remains deferred to a separate session.

See [IAM evidence](2026-10-12_horology-deployer-impersonation_note.md). Protected administrator Owner remains intentional for now.
