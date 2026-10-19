# Gateway access: one shared policy, Audience sign-in, daily and monthly budgets

## Topic
- gateway-shared-policy-and-budgets

## Context

The gateway began with operator-provisioned, expiring assignments: each client got its own tool list, expiry and per-assignment caps (two paid calls per provider, per-tool counts), and Google sign-in mapped an approved email to an assignment. That needed fresh provisioning for every scheduled run and kept two email lists in step. The cloud policy, which holds no credentials, also lived in Secret Manager, so the deployed policy couldn't be reviewed in Git and the laptop copies drifted.

## Decisions

**Only shared daily and monthly budgets (2026-10-13).** The operator withdrew session-based caps. Per-tool counts, per-assignment credit caps and per-provider call caps were removed. Firecrawl and Tavily each keep 50 credits per UTC day and 500 per calendar month, shared across every client, reserved atomically under the coordinator row lock using database time. History and cache were kept; nothing was reset or refunded.

**No assignments (2026-10-13).** The policy is one shared `access` block with the same tools and resource scopes. Assignment selection, expiry and email-to-assignment mappings are gone; local bearer hashes are a JSON list. Client IDs now identify requests and cache namespaces only. Migration `20261013_001` renamed the usage and cache columns to `client_id` without rewriting rows. Every other check stayed: schema bounds, the forbidden auth schema, Alexandria bounds, public-address checks, exact Tavily extraction URLs, identity verification, nonce, cookie and redirect checks, consent, token lifetimes, grant rotation and revocation. The descriptive `disabled_access_ids` field was dropped from policies and `gateway_status`; named tools in JSON are the only authority.

**Sign-in managed in Google Auth Platform → Audience (2026-10-13).** The app is External with status Testing, and only listed test users can complete Google sign-in, so people are added and removed in a console. The gateway keeps no email list of its own. IAP and Cloud Run IAM were ruled out, because Claude, ChatGPT and Codex connectors run the MCP OAuth flow from their own servers and can't pass IAP or send Google identity tokens. A welladino.com domain rule wouldn't fit, because the operator signs in with a Gmail address. At sign-in, the gateway stores the verified email (lower-cased, in plain text in the grant's JSON; the only personal data it keeps) on every code, access and refresh record, so `scripts/revoke_email.py` can delete one person's tokens.

**Policy baked into the image (2026-10-13).** `config/policy.cloud.json` is tracked and copied to `/config/policy.json`; a policy change already needed a new revision, and a credential-free file is easier to review. Local Compose mounts the ignored `policy.local.json` over it. The image check loads the baked policy, and a test asserts it has no credential-like fields. The previous Secret Manager version was kept as an ignored local snapshot for rollback. The release dropped `GATEWAY_OAUTH_ASSIGNMENTS`, `GITHUB_TOKEN`, `GATEWAY_TOKEN_HASHES` and both policy volumes. Private manual-test clients moved to `tests/manual/gateway/fixtures/private/`, ignored and excluded from Cloud Build uploads.

## Rationale

Spending is what needs a hard limit, and a shared daily and monthly cap gives it without per-run provisioning. One access list in a console replaces two lists that could disagree, and a policy in Git is reviewed like code.

## Impact

- Accepted risk: publishing the Google app ("In production") would let any Google account sign in, because there is no second check. Keep it in Testing.
- Removing an Audience user blocks new sign-ins only; a connected client keeps refreshing (7-day refresh lifetime, rotated on use) until `revoke_email.py` is run. Grants issued before emails were recorded can't be matched by email.
- Current state: [gateway policy and budgets](../../architecture/mcp/gateway.md#policy), [sign-in](../../architecture/mcp/mcp-services.md#sign-in).

## Follow-Ups

- Verify live revocation end to end.
