# Direct Horology deployer impersonation

Date: 2026-10-12

## Decision and scope

The protected administrator grants the daily user direct Token Creator on `horology-deployer@horology-dev.iam.gserviceaccount.com`. No deployment group, folder policy or Terraform is introduced. Existing organization/folder IAM and AAA are unchanged. Protected `gcp-deployment@welladino.com` retains its existing Horology Owner role for administration; routine operations use the restricted service account.

The existing developer group receives Horology Viewer, Logging Viewer and Monitoring Viewer. Custom role definitions live in `ops/gcp/iam/`. The deployer can submit/read builds, inspect logs/services, update only the existing gateway and document-graph services, upload/read source only in the build-source bucket, read images and update tags only in the MCP registry, and act as only the build/gateway/document-graph identities. It cannot delete services, edit IAM, create service-account keys, read/change secret values or enable APIs.

## CLI profiles

- `horology`: daily account with deployer impersonation; existing gcloud MCP configuration uses this profile.
- `horology-view`: daily account without impersonation for read-only viewing.
- `horology-admin`: protected administrator, no impersonation, explicit privileged administration.

No service-account keys were created. Existing CLI user credentials were refreshed by the operator. ADC was not changed; CLI configuration does not configure SDK credentials automatically.

## Verification

- Daily-account impersonation lists both services. The `horology-view` profile also lists both directly, without impersonation.
- Resource IAM permission tests show update allowed and delete/setIamPolicy denied on both services.
- Act-as checks pass on the three named identities; getAccessToken, key creation and setIamPolicy are absent there.
- Gateway database secret access, version addition, deletion and IAM editing are denied to the deployer.
- Both Cloud Run services pass `validateOnly=true` deployment validation; service generation and ready revision remain unchanged.
- [Build affdb8cc-aec5-4eea-bd78-a201bbaa6dae](https://console.cloud.google.com/cloud-build/builds;region=us-central1/affdb8cc-aec5-4eea-bd78-a201bbaa6dae?project=horology-dev) was submitted/uploaded through daily-account impersonation: 69 tests passed, nine expected local-stack skips, all dependency audits and image contracts/blocking scans passed. New images were published; they were not deployed.
- Protected administrator project-policy readback confirms scoped build/read grants, developer-group read grants and the retained administrator Owner binding.
- Project-level REST permission testing was unavailable because Cloud Resource Manager API is disabled for the service-account consumer project; no API was enabled. Required service-level tests and actual build/deployment validation passed.

Temporary automatic-approval service rate limits interrupted some grants/config reads. Affected mutations were retried through the same approval path and succeeded; no approval controls were bypassed.

See [IAM runbook](../../runbook/architecture/gcp_access.md). No commit or push.
