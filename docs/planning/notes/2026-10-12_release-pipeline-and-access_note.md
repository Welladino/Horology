# Release pipeline and deployment access

## Topic
- release-pipeline-and-access

## Context

After the first Cloud Run deployment, releases needed repeatable checks before publishing, image retention that wouldn't grow without limit, and a routine way to deploy that didn't use the protected administrator account. The consent page also needed to tell people clearly what they were approving.

## Decisions

**Cloud Build from uploaded source (2026-10-12).** Release images are built in Cloud Build from manually uploaded local source; GitHub stays version control, with no deployment trigger or branch protection. The private source bucket deletes objects after 7 days. A dedicated `mcp-build` identity can read the bucket, write build logs and publish only to `mcp-servers`. Blocking gates: source secret and Dockerfile scans, tests against disposable PostgreSQL (unexpected skips fail the build), pip-audit, the runtime image contract (UID 10001, no pip, setuptools or wheel, required assets) and image scans for fixable High/Critical vulnerabilities and secrets. With the operator's approval, unfixed findings are reported but don't block. Artifact Registry keeps five recent versions per package plus anything tagged `deployed-`; the live digests are tagged `deployed-current`. Local Docker keeps one `latest` per server. First successful build: [f4825b13](https://console.cloud.google.com/cloud-build/builds;region=us-central1/f4825b13-97d6-48f4-9215-62d271d23778?project=horology-dev), 69 tests passed with 9 expected local-stack skips; each image showed 44 unfixed High and zero Critical OS findings.

**Readable consent page (2026-10-12).** The page shows the signed-in account, the requesting client and plain permission groups, with tool names in an expandable list. Cookie checks, single-use consent and the callback-origin CSP exception are unchanged; no external assets, scripts or extra Google scopes.

**Routine deploys through impersonation (2026-10-12).** The protected administrator granted the daily account Token Creator on `horology-deployer` only. Custom roles in `ops/gcp/iam/` let the deployer submit and read builds, read logs and services, update only the two existing services, upload only to the source bucket, read and tag only in `mcp-servers`, and act as only `mcp-build`, `mcp-gateway` and `document-graph`. It can't delete services, edit IAM, create keys, read or change secrets, or enable APIs. The developer group got Viewer, Logging Viewer and Monitoring Viewer. Three gcloud configurations (`horology`, `horology-view`, `horology-admin`) separate routine, read-only and privileged use; no service-account keys exist. Verified with resource permission tests, `validateOnly=true` deployments and a real build submitted through impersonation ([affdb8cc](https://console.cloud.google.com/cloud-build/builds;region=us-central1/affdb8cc-aec5-4eea-bd78-a201bbaa6dae?project=horology-dev)). Project-level permission tests needed the Cloud Resource Manager API, which stayed disabled rather than being enabled from the routine account.

**Global Cloud Build endpoint for the free tier (2026-10-13).** October's bill showed $0.47 for about 62 build-minutes, with no free-tier saving. Regional `us-central1` builds bill the E2 CPU and RAM SKUs from the first minute; the only SKU with a free tier (2,500 minutes, then $0.006 a minute) is "Build time e2-standard-2" in region `global` (catalog read 2026-10-13). Builds are now submitted without `--region`; `cloudbuild.yaml` keeps `E2_STANDARD_2` and `CLOUD_LOGGING_ONLY`, which the custom service account requires. If an organisation policy refuses global builds, go back to `--region=us-central1`.

**Image-check layout (2026-10-13).** The image-contract script runs inside the image, where packages live under `/app`, so it uses explicit `importlib` imports and symbol lookups; a missing package or symbol still fails. The Artifact Registry clean-up policy moved to `ops/gcp/artifact-cleanup.json`, as operator-applied configuration rather than a build step. Build `1ae022ce` on commit `d643223` passed with 106 tests and an upload of 76 files that left out private policies, test clients and parked connectors.

## Rationale

Every gate runs before anything is published; routine access is the narrowest that still lets one person release, and privileged administration stays a deliberate, separate path.

## Impact

- Current state: [Cloud](../../architecture/cloud/cloud-infrastructure.md). Commands: [Cloud Build](../../runbook/gcp/cloud_build.md), [operator checks](../../runbook/gcp/operator_checks.md).
- GitHub Actions now runs the same gates on every push, plus a full-history gitleaks scan, and licence gates were added.

## Follow-Ups

- Confirm on the bill that global builds land on "Build time e2-standard-2" with the free tier applied.
- Review unfixed Debian findings as base-image fixes appear; update the pinned Trivy deliberately and re-test the gates.
- Folder-wide developer visibility and project provisioning are deferred.
