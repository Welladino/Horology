# MCP release builds

Start with the [Cloud architecture](../../architecture/cloud/README.md) for the release pipeline and identities, and [MCP services](../../architecture/mcp/README.md) for sign-in. Day-to-day checks: [operator access and checks](operator_checks.md).

Run from the Horology repository root. Cloud Build receives source, runs mocked provider/security tests against disposable PostgreSQL, audits Python dependencies, builds both images, then scans them with Trivy. A failed gate prevents publication. Real provider keys and production databases are never used by tests. The local Hermes Docker stack tests skip because the build has no Docker CLI/runtime credentials; gateway persistence tests must run.

See [operator access and checks](operator_checks.md) for the gcloud configurations and impersonation.

## Submit

```bash
gcloud --configuration=horology builds submit . --project=horology-dev --config=cloudbuild.yaml --gcs-source-staging-dir=gs://horology-dev-mcp-build-source/source --service-account=projects/horology-dev/serviceAccounts/mcp-build@horology-dev.iam.gserviceaccount.com
```

Submit to the global endpoint (no `--region`). Only global builds on e2-standard-2 use the free-tier SKU "Build time e2-standard-2" (2,500 minutes a month per billing account); `--region=us-central1` builds are billed per vCPU and GiB from the first minute. See the [note](../../planning/notes/2026-10-12_release-pipeline-and-access_note.md). Images still go to the `us-central1` Artifact Registry.

First configure the build identity with Artifact Registry Writer on the `mcp-servers` repository, Logs Writer in the project, and Storage Object Viewer on `horology-dev-mcp-build-source`. That private source bucket deletes uploads after seven days (GCS soft-delete retention can extend physical storage). The submitting account needs permission to submit builds and act as this service account. The builder needs no provider secrets or Cloud Run deployment privileges. Cloud Build API must be enabled.

Check `.gcloudignore` with `gcloud meta list-files-for-upload` before submitting. It uploads only build inputs; `.dockerignore` separately limits runtime image contents.

## Deploy

After a successful build, inspect its image digests and deploy by digest using the existing service identities, environment and secret mappings. Do not deploy `latest` directly. Deployment is a separate operator action; this pipeline does not auto-deploy or migrate production databases.

Before enabling cleanup, tag each currently deployed digest `deployed-current`. Move that tag to the replacement digest after a verified deployment. Preserve any intentionally retained rollback image with another `deployed-` tag; remove that tag when no longer needed.

```bash
gcloud --configuration=horology artifacts docker tags add us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:DEPLOYED_DIGEST us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway:deployed-current --project=horology-dev
gcloud --configuration=horology-admin artifacts repositories set-cleanup-policies mcp-servers --project=horology-dev --location=us-central1 --policy=ops/gcp/artifact-cleanup.json --no-dry-run
```

Protect document-graph's deployed digest in the same way before applying the repository policy. Retention keeps five recent versions **per image package**, plus deployed/rollback versions if older. Cleanup runs asynchronously, approximately daily; it is not an immediate hard cap of five. Container manifest references may preserve additional child versions.

## Local images

Use Docker Compose for local testing; keep its single `latest` tag per service. Remote release versions are created by Cloud Build's unique build ID. Never run a global Docker prune to remove unrelated project images.

## Reports and limitations

Cloud Build logs contain pytest/audit/scanner results in Cloud Logging. JUnit is written under `/workspace/reports` during the build; configure a report bucket if persistent downloadable JUnit is needed. Scans report all HIGH/CRITICAL image vulnerabilities, then block HIGH/CRITICAL vulnerabilities with available fixes, secrets and infrastructure misconfiguration; they do not replace a manual security review. Scanner versions are pinned; review upgrades and vulnerability database availability periodically. No broad ignore lists or `allowFailure` bypasses.

## Moving an existing deployed tag with restricted IAM

The routine deployer has tags.update but no tags.delete. The gcloud docker tags add command can delete/recreate an existing tag and fails in that case. Use Artifact Registry's tags.patch API with updateMask=version to move an existing deployed-current tag, keeping the restricted IAM unchanged. Authenticate through the horology configuration, hold the resulting access token only in process memory, and verify the returned version equals the deployed digest. See [the verified rollout note](../../planning/notes/2026-10-12_gateway-provider-scope_note.md).
