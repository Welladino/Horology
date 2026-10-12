# Initial private Cloud Run MCP deployment

## Topic
- cloud-run-mcp-deployment

## Context
- Continue the agreed deployment plan after Neon accounting. The operator enabled required APIs in horology-dev.

## Decision
- Deploy gateway and document graph separately in us-central1, with IAM invocation required, separate runtime identities and service-specific versioned secrets. No Terraform, Firestore or public invoker grant.
- Shared runtime settings now support PORT, configurable gateway public URL and stateless JSON MCP requests. Existing local ports remain available.
- Start with 1 CPU, 512 MiB, concurrency 4, max instances 1, minimum 0, request-based billing and 60-second request timeout. These settings do not impose a hard billing cap.

## Rationale
- Cloud Run routes independent requests across instances; fixed tools need no in-memory MCP sessions. Persistent quotas remain in Neon. Secrets are excluded from images and stored in Secret Manager.

## Impact
- Artifact Registry repository mcp-servers and two runtime identities created. Nine secrets uploaded as version 1; each runtime identity can read only its service's secrets.
- Separate cloud test assignment provisioned for 24 hours. Google tools are unassigned. Per-run automated provisioning and OAuth remain pending.
- Gateway revision mcp-gateway-00002-df9 and graph revision document-graph-00001-k69 verified. Endpoints, image digests and secret mappings are recorded in the [runbook](../../runbook/gcp/mcp_deployment.md).
- No paid provider calls, document writes or embeddings were made in deployment checks. Temporary plaintext upload files and local test containers were removed after verification; private cloud client/policy files remain ignored by Git.

## Verification
- 61 full repository/gateway tests passed, including disposable Postgres quota checks and Cloud Run configuration tests.
- Both Linux amd64 images built and passed real MCP initialization locally at PORT=8080. Gateway: 17 tools, rejected invalid auth and denied scopes; graph: seven tools.
- Existing Docker network test changed from a bare streaming GET to a bounded invalid JSON-RPC POST.
- Cloud checks: unauthenticated requests rejected for both services; gateway rejects missing/invalid assignment bearer even with valid IAM authentication; correct public resource URL in auth metadata; authenticated MCP initialization/discovery and gateway scope denials passed.
- No allUsers invoker bindings on either service. No direct scheduled-client connection was tested.

## Follow-Ups
- Test provider calls from cloud minimally, including quota history across revision replacement and safe connection failures.
- Verify document-graph cloud DB access and bounded embedding usage before enabling cloud writes.
- Implement client-compatible OAuth and automated per-run assignments; complete Google provider OAuth before enabling Drive.
- Set an operator-chosen billing alert and review image/log retention. Keep scheduling deferred until client access works.
- Changes remain uncommitted and unpushed.
