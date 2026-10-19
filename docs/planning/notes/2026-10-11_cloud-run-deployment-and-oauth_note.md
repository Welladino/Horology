# Cloud Run deployment and Google sign-in

## Topic
- cloud-run-deployment-and-oauth

## Context

Subscription agents run in the cloud, so the gateway and document graph had to be reachable from there with protected credentials, durable quotas and proportionate cost, using direct gcloud commands rather than Terraform. Project `horology-dev` (display name `horology`) had billing enabled.

## Decisions

**Plan (2026-10-11).** Region `us-central1`, a Cloud Run Tier 1 region and the pricing basis for the free-tier discount (replacing earlier Singapore and South Carolina proposals). The free allowance is shared across the billing account, not per project, so this guarantees no zero bill; image storage, builds, secrets, networking and Neon are priced separately ([Cloud Run pricing](https://cloud.google.com/run/pricing), checked 2026-10-11). Quotas stay in the existing Neon database rather than adding Firestore, because Cloud Run's local files don't survive instance replacement. Two separate services, both packaging the shared runtime; the Supabase CA stays in the gateway image.

**First private deployment (2026-10-11).** Artifact Registry `mcp-servers`, one runtime identity per service, nine secrets in Secret Manager (version 1), each identity able to read only its own. Both services started IAM-only: 1 CPU, 512 MiB, concurrency 4, at most 1 instance, minimum 0, request-based billing, 60-second timeout. The shared runtime gained `PORT`, a configurable public URL and stateless JSON MCP requests: fixed tools need no in-memory session, so Cloud Run can route each request anywhere. Checks: 61 tests passed; both images initialised locally on port 8080; in the cloud, unauthenticated requests were refused, the gateway refused a missing or wrong bearer even with valid IAM, and authenticated discovery and scope denials worked. No `allUsers` invoker binding existed.

**Google-backed MCP sign-in for the gateway (2026-10-11).** The gateway is the MCP authorisation server; Google only proves identity with `openid email`, so no Drive or Gmail access is granted. Implemented: discovery, dynamic client registration, PKCE, token and revocation endpoints; one-time login state, nonce and a secure HttpOnly cookie; Google ID tokens verified against its JWKS for audience, issuer, expiry, nonce and verified email; explicit consent. Opaque tokens are stored as SHA-256 hashes in `gateway_auth.records` (migration `20261011_002`); code exchange, refresh rotation and revocation are serialised in database transactions, so a concurrent refresh can't revive a revoked grant. Access tokens last 15 minutes, refresh tokens at most 7 days. Signing in or refreshing never resets spending. Callback queries are kept out of logs, and the `_Default` logging sink excludes `/auth/` and `/authorize` URLs. 76 tests passed.

**Public ingress, application sign-in (2026-10-11).** With the operator's explicit approval, the gateway's invoker IAM check was turned off so external clients can reach discovery and sign-in; every MCP tool still requires a gateway token (revision `mcp-gateway-00004-25t`). The document graph stayed IAM-only until it got its own sign-in ([note](2026-10-13_document-graph-workspaces-signin-and-sync_note.md)).

**Consent page fix (2026-10-11 to 10-12).** Chrome blocked the consent form under `form-action 'self'`, because it applies `form-action` to the POST's final redirect to the client's loopback callback. The page now allows its own origin plus only the SDK-validated callback origin, including its port; registration rejects host strings that could inject CSP directives. On 2026-10-12 a fresh Codex login completed in a single tab.

## Rationale

Reuse existing Postgres for transactional accounting rather than add a database, keep each service's secrets and identity separate, and keep reachability (public HTTPS) and authorisation (OAuth) as separate, deliberately chosen properties.

## Impact

- Current state: [Cloud](../../architecture/cloud/cloud-infrastructure.md), [MCP sign-in](../../architecture/mcp/mcp-services.md#sign-in). Commands: [deployment runbook](../../runbook/gcp/mcp_deployment.md).
- The assignment model used at first was replaced by one shared policy and Audience-managed sign-in ([note](2026-10-13_gateway-shared-policy-and-budgets_note.md)).

## Follow-Ups

- Choose a billing alert amount with the operator; alerts notify, they don't cap.
- Verify minimal live provider calls from the cloud, quota survival across revision replacement under parallel calls, and safe errors on connection failure.
- Verify each intended scheduled client (Codex, Claude, ChatGPT) can sign in and refresh unattended before creating schedules.

Sources: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect), [MCP SDK authorisation](https://py.sdk.modelcontextprotocol.io/run/authorization/), [Cloud Run file system](https://docs.cloud.google.com/run/docs/container-contract#file_system), [MDN form-action](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/form-action).
