# Operator access and checks

How the identities fit together: [Cloud architecture](../../architecture/cloud/cloud-infrastructure.md#identities).

## gcloud configurations

`horology`, `horology-view` and `horology-admin` are named gcloud configurations on the laptop, all targeting `horology-dev`; they are not GCP resources.

```bash
gcloud config configurations list
```

```bash
gcloud config configurations describe horology
```

Sign in the routine configuration (daily account, impersonating `horology-deployer`):

```bash
gcloud --configuration=horology auth login saravanaraj.subramaniam@welladino.com
```

```bash
gcloud --configuration=horology run services list --project=horology-dev --region=us-central1
```

Read-only viewing, no impersonation:

```bash
gcloud --configuration=horology-view run services list --project=horology-dev --region=us-central1
```

Protected administration (IAM, new resources, secrets, the sync job):

```bash
gcloud --configuration=horology-admin projects get-iam-policy horology-dev
```

The gcloud MCP sets `CLOUDSDK_ACTIVE_CONFIG_NAME=horology`, so changing the terminal's active configuration doesn't change it.

## After a deploy

These make no paid provider calls. Expected: OAuth discovery `200` for both services, anonymous MCP `401` for both.

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://mcp-gateway-366292507424.us-central1.run.app/.well-known/oauth-authorization-server
```

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://mcp-gateway-366292507424.us-central1.run.app/mcp -H 'Content-Type: application/json' -d '{}'
```

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://document-graph-366292507424.us-central1.run.app/.well-known/oauth-authorization-server
```

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://document-graph-366292507424.us-central1.run.app/mcp -H 'Content-Type: application/json' -d '{}'
```

Then call `gateway_status` and `list_documents` from a connected client.

## Build results

Replace `BUILD_ID`. Builds submitted up to 2026-10-13 ran regionally; add `--region=us-central1` for those.

```bash
gcloud --configuration=horology builds describe BUILD_ID --project=horology-dev --format='json(status,results.images)'
```

```bash
gcloud --configuration=horology builds log BUILD_ID --project=horology-dev
```

Steps worth opening in the Console: `source-security`, `tests-and-dependency-audit`, `verify-*-image`, `report-*-vulnerabilities` (unfixed findings), `scan-*` and `licences-*` (blocking).

## Image storage

Read-only:

```bash
gcloud --configuration=horology artifacts docker images list us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway --include-tags --project=horology-dev
```

```bash
gcloud --configuration=horology artifacts repositories describe mcp-servers --location=us-central1 --project=horology-dev --format='json(cleanupPolicies,cleanupPolicyDryRun)'
```

Clean-up runs about daily, so more than five rows can show for a while. Protection tags: [Cloud Build](cloud_build.md).

## Revoking routine deploy access

The protected administrator removes the daily account's Token Creator grant on `horology-deployer`. Tokens already minted stay valid until they expire.
