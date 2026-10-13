# Implementation Note

## Topic
- audience-signin-baked-policy

## Context
- The gateway's cloud policy holds no credentials (tool names, budget caps, Supabase project ref, URL rules), yet was stored as Secret Manager `horology-gateway-policy` and mounted at `/config/policy.json`.
- Sign-in was gated twice: Google sign-in, then a gateway-side email list (`GATEWAY_OAUTH_ASSIGNMENTS`, later `GATEWAY_OAUTH_ALLOWED_EMAILS`). The operator wanted to add and remove people in a console instead of editing an environment variable.
- IAP and Cloud Run IAM were ruled out: Claude/ChatGPT/Codex connectors use the MCP OAuth flow from their own servers and cannot pass IAP sign-in or send Google identity tokens.

## Decision
- Who may sign in is managed in Google Auth Platform → Audience (External, status Testing, test users). The operator set the app to External on 2026-10-13. The gateway no longer keeps an email list; `GoogleOAuthProvider` takes no `allowed_emails` and accepts any identity Google verifies for this client.
- The cloud policy is tracked at `mcp-servers/mcp-gateway/config/policy.cloud.json` and copied into the image at `/config/policy.json`. Local Compose still mounts `policy.local.json` over that path.
- The previous Secret Manager snapshot was kept as ignored `config/policy.cloud.secret-v4.local.json` for rollback reference.
- The cloud release drops `GATEWAY_OAUTH_ASSIGNMENTS`, `GITHUB_TOKEN`, `GATEWAY_TOKEN_HASHES` and both policy volumes (versions 3 and 4, one of them unmounted). Steps are in `docs/runbook/gcp/mcp_deployment.md`.

- Revoke by email: at sign-in the gateway now keeps the Google-verified email (lowercased) on the grant and copies it into every `code`, `access` and `refresh` record in `gateway_auth.records`. `scripts/revoke_email.py` deletes that person's `access` and `refresh` records. **The email is stored in plain text in the records' `data` JSON in Neon**; it is the only personal data the gateway stores. Grants issued before this change have no email and are not matched.

## Rationale
- A credential-free file is easier to review and version in Git than a secret; a policy change already required a new revision either way.
- Audience gives a console list without gateway code. The operator signs in with a Gmail address, so a welladino.com domain rule would not fit.

## Impact
- Tests: 96 passed, 23 skipped (Docker unavailable). Added checks that the baked policy loads and contains no credential-like fields, and that the provider has no email allowlist. `scripts/ci/check_image.py` now loads `/config/policy.json` inside the built image. The image build itself was not run locally.
- Accepted risks: if the app is published ("In production"), any Google account can sign in, because the gateway has no second check. Removing a test user blocks new sign-ins only; a connected client keeps refreshing gateway tokens (7-day refresh lifetime, rotated on use) until `scripts/revoke_email.py` is run for that email.
- No cloud service, secret, migration or deployment was changed.

## Follow-Ups
- Run the release steps in the deployment runbook.
- Existing grants (the operator's own sign-ins before release) carry no email. To cut those off, revoke them by grant or sign in again after release.
