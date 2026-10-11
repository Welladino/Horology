# Implementation Note

## Topic

2026-10-11 — Verified TLS trust for the gateway’s Supabase connection.

## Context

The founder approved configuring certificate trust while keeping full server verification. The initial gateway failed because libpq expected an unavailable root certificate.

## Decision

Tested `PGSSLROOTCERT=system` with the container CA bundle. The pooler failed validation with “self-signed certificate in certificate chain”, so system roots alone were insufficient. Final configuration uses Supabase’s official public CA, saved outside Git at `~/.local/share/horology/certs/supabase-prod-ca-2021.crt`. An ignored `.env.local` variable `SUPABASE_CA_FILE` supplies the host path; Compose mounts it read-only at `/certs/supabase-ca.crt` and sets `PGSSLROOTCERT` to that path. The existing adapter retains `sslmode=verify-full`.

## Rationale

The public CA verifies the server certificate chain; hostname verification remains enabled. The trust anchor was obtained from the HTTPS download URL in Supabase’s official dashboard source, not copied from an untrusted server handshake. No certificate, private key or credential was committed to source control.

Official source: https://raw.githubusercontent.com/supabase/supabase/master/apps/studio/hooks/custom-content/custom-content.json

Download: https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt

DER certificate SHA256: `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`.

## Impact

Compose commands now require `--env-file .env.local` for host-path interpolation. The environment template includes `SUPABASE_CA_FILE`. Recreated only the gateway container, preserving budget history. No roles, passwords, permissions, application data or server-side SSL enforcement settings changed.

Verification: 39 tests passed; 14 unrelated main-stack Docker tests skipped. Real connection from the container passed full TLS validation and authenticated as `horology_agents` using TLS 1.3, without executing SQL. MCP handshake, 13-tool discovery, authentication and scope-denial checks passed. Metadata/performance reads were not repeated because their current test-assignment quotas were already exhausted; no counters were reset.

## Follow-Ups

Verify metadata permissions in a future bounded assignment. Maintain the externally mounted public CA through deployment configuration; revalidate its provenance on rotation. Google OAuth remains deferred.
