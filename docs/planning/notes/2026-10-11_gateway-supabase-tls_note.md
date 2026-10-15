# Gateway TLS to Supabase: the official public CA in the image

## Topic
- gateway-supabase-tls

## Context

The gateway's Supabase metadata connection uses `sslmode=verify-full`, which checks both the certificate chain and the hostname. The first start failed because libpq expected a root certificate that wasn't there. The founder approved configuring trust, provided full verification was kept.

## Decisions

**System roots aren't enough (2026-10-11).** `PGSSLROOTCERT=system` with the container's CA bundle failed against the pooler ("self-signed certificate in certificate chain").

**Use Supabase's official public CA (2026-10-11).** The trust anchor was downloaded over HTTPS from the URL in Supabase's own dashboard source, not copied from a server handshake:

- Listed in: https://raw.githubusercontent.com/supabase/supabase/master/apps/studio/hooks/custom-content/custom-content.json
- Download: https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt
- DER SHA-256: `807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`

It first lived outside Git and was mounted through a `SUPABASE_CA_FILE` path. At the founder's request it moved into the repository at `mcp-servers/mcp-gateway/certs/supabase-prod-ca-2021.crt`; it is a public trust anchor, not a credential. The Dockerfile now packages it at `/certs/supabase-ca.crt` and sets `PGSSLROOTCERT`, so local Compose and Cloud Run use the same image with no host mount. The root `.dockerignore` lets in only this named certificate.

Each step was verified the same way: unchanged fingerprint, a live connection authenticated as `horology_agents` over TLS 1.3 with `verify-full` (no SQL run), and the MCP handshake, tool discovery and scope-denial checks, with quota history preserved.

**Neon uses certifi (2026-10-11).** The gateway's own Neon connection verifies against certifi's public bundle with `verify-full`, overriding the Supabase-specific `PGSSLROOTCERT` for that connection only.

**GitHub token rejected (2026-10-11).** While checking the bundled image, one bounded `GET https://api.github.com/user` returned 401, so no repository calls were made. The GitHub adapter was later removed altogether.

## Rationale

Full verification with a trust anchor of known provenance; a checked-in public certificate makes the image portable and removes a machine-specific path.

## Impact

- The image contract in Cloud Build checks the CA is present ([Cloud](../../architecture/cloud/README.md#release)).

## Follow-Ups

- When Supabase rotates its root certificate, re-check provenance, then update the file and the fingerprint here.
