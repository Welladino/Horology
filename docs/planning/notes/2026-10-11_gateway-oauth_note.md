# Gateway OAuth with Google identity

Google establishes the approved owner's identity using OpenID Connect. The gateway is the MCP OAuth authorization server. Google credentials and tokens are never passed to MCP clients, and the requested Google scopes are only `openid email`. This does not authorize Google Drive.

## Implementation

- OAuth SDK discovery, dynamic client registration, PKCE, token and revocation endpoints.
- Separate Google start/callback routes with one-time login state, nonce verification, a secure HttpOnly cookie and explicit client consent.
- Verify Google's signed ID token against its official JWKS, audience, issuer, expiry, nonce and verified email. Only the server-configured email-to-assignment mapping can grant access.
- Opaque access/refresh credentials are stored by SHA-256 in Neon `gateway_auth.records`; clients, state and grants expire. Alembic revision `20261011_002` is applied.
- Database transactions serialize code exchange, refresh rotation and revocation. A concurrent refresh cannot revive a revoked grant.
- Access tokens last at most 15 minutes; refresh tokens at most seven days. Both are capped by the existing policy assignment expiry. Lifetimes live in shared-runtime settings.
- OAuth claims resolve to the same assignment used by tool authorization and quota accounting. Login and refresh never reset counters or extend assignments.
- Legacy assignment tokens remain supported for local clients and the existing short-lived cloud smoke assignment.
- Application access logs omit callback queries. Cloud Logging's `_Default` sink excludes gateway `/auth/` and `/authorize` request URLs; structured tool/error logs remain available. Audit logs are retained. Any future extra log sink needs the same exclusion.

## Cloud inputs

`GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are in the gateway's private `.env.local` and service-specific Secret Manager secrets, pinned to version 1. The allowed-account mapping is `GATEWAY_OAUTH_ASSIGNMENTS`; `GATEWAY_OAUTH_ENABLED=true` enables the provider. Local Compose remains on assignment tokens unless explicitly enabled with a matching local redirect URI.

The new owner-interactive assignment lasts 30 days from provisioning and inherits the approved tools, two repositories and existing limits. Each paid provider still allows only two calls for that assignment, 50 credits/day and 500/month globally. This assignment is for connection testing and direct use; it is not scheduled-agent provisioning. A scheduler must later provision independent authorized assignments without deleting quota history.

Only the gateway will accept external HTTP requests for OAuth discovery and sign-in. `/mcp` requires a verified gateway credential. Document graph retains Cloud Run IAM protection.

## Validation

76 tests passed with disposable Postgres and the existing Docker stack. Coverage includes approved-account/consent rejection, callback cookie/state validation, wrong signed identity claims, redirect/resource restrictions, SDK PKCE, code replay, token refresh and grant revocation, assignment expiry and concurrent database operations. Upstreams are mocked in these tests.

Private cloud smoke passed discovery, registration, Google redirect, invalid callback rejection and existing authenticated MCP initialization with 17 tools. Final browser login and native Codex tool access require the operator's Google sign-in. No paid provider calls or document-graph writes were made during OAuth deployment checks.

Sources: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect), [MCP SDK authorization](https://py.sdk.modelcontextprotocol.io/run/authorization/), [OpenAI MCP authentication](https://developers.openai.com/plugins/build/auth), [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
