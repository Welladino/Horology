# Remove gateway assignments

Date: 2026-10-13

The operator requested complete assignment removal, leaving revocation verification for the later Cloud Build/release phase. Runtime policy now contains one shared `access` block with the previous approved tools and resource scopes. Preserved schema bounds, forbidden Auth schema, Alexandria operation/country bounds, HTTPS/public-address validation, exact Tavily extraction targets, OAuth approved-email checks, identity verification, nonce/cookie/redirect checks, consent, token TTLs and client grant rotation/revocation.

Removed assignment selection, authorization expiry, per-assignment OAuth fields and email-to-assignment mappings. Local bearer hashes are a JSON list; OAuth approved emails use GATEWAY_OAUTH_ALLOWED_EMAILS. Client IDs identify requests and cache namespaces; they do not select separate permissions or spending caps. Daily/monthly provider accounting spans all clients and retains all history.

Prepared Alembic 20261013_001 to rename usage/cache columns and indexes without deleting or rewriting rows. Runtime startup checks require the renamed columns. Existing stored OAuth records may retain historical assignment fields; new credentials omit them and runtime authorization ignores them. No production migration was applied, no credentials revoked and no cloud policy/deployment changed. A release must update the policy/environment and apply the rename migration before the new image serves traffic.

Automatic approval review rejected two broad scripted edits; they were replaced with targeted policy/OAuth/verifier changes that preserved provider resource checks. Local verification: 92 tests passed; 19 infrastructure tests skipped with Docker unavailable. Live OAuth revocation and database-backed release checks remain pending. No Cloud Build, deployment or commit ran.
