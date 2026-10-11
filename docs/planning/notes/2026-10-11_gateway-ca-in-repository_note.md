# Implementation Note

## Topic

2026-10-11 — Include the official public Supabase CA in the gateway repository.

## Context

The founder explicitly requested moving the public CA from `~/.local/share/horology/certs/supabase-prod-ca-2021.crt` into Horology. This supersedes the external-file location recorded in the earlier TLS note.

## Decision

Move the file to `mcp-servers/mcp-gateway/certs/supabase-prod-ca-2021.crt`. Mount it read-only using a relative Compose path at `/certs/supabase-ca.crt`. Remove the obsolete `SUPABASE_CA_FILE` variable from the ignored local environment and initializer. Update startup commands and standing architecture/setup documentation. Keep `PGSSLROOTCERT` pointed at the mounted file and retain `sslmode=verify-full`.

## Rationale

This is a public CA trust anchor, not a database credential or private key. Including it makes the local checkout portable and removes a machine-specific host path.

Official source: https://raw.githubusercontent.com/supabase/supabase/master/apps/studio/hooks/custom-content/custom-content.json

Download: https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt

DER certificate SHA256: `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`.

## Impact

The original external file was moved, not retained as a second copy. Database credentials and the persistent quota volume were preserved. The Docker image still excludes local configuration; Compose supplies the CA mount. Future cloud deployment must explicitly supply this public CA to its runtime.

Verification: certificate fingerprint unchanged; 39 tests passed, 14 unrelated main-stack Docker tests skipped. Live Supabase TLS and `horology_agents` authentication passed using TLS 1.3 without executing SQL. MCP initialization, tool discovery, authentication and scope-denial checks passed. No provider charges, database changes or quota resets.

## Follow-Ups

Review official CA provenance and update this file/fingerprint when Supabase rotates its root certificate. Google OAuth remains deferred.
