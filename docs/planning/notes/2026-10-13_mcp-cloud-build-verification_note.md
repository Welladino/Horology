# MCP cloud build verification

Source commit: `d643223` (local only; not pushed). Build `1ae022ce-3223-436d-a6b4-df9bd65a0c5c` succeeded in horology-dev/us-central1 on 2026-10-13 (Asia/Singapore).

[Cloud Build results](https://console.cloud.google.com/cloud-build/builds;region=us-central1/1ae022ce-3223-436d-a6b4-df9bd65a0c5c?project=horology-dev).

## Reviewed checks

- Source secrets/misconfiguration gate passed.
- Disposable PostgreSQL migrations and tests: 106 passed, nine expected local Docker-stack skips. The gateway persistence checks ran under the restricted role.
- Both server dependency audits and installed CI environment audit reported no known vulnerabilities.
- Both images passed runtime contracts, including non-root execution, required assets/imports and exclusion of private/parked integrations.
- Each image report contains 44 unfixed High OS findings and zero Critical findings. Blocking scans for fixable High/Critical vulnerabilities and detected secrets passed. Unfixed reports remain follow-up work, not resolved findings.
- Upload allowlist included 76 files, excluding private policies/test clients and parked connectors.

## Published images

- Gateway: `us-central1-docker.pkg.dev/horology-dev/mcp-servers/mcp-gateway@sha256:e934ee8a9e872dbbeecaaf3e4471c035fa265defc8569d0f9e9e35ae4ae6817a`
- Document graph: `us-central1-docker.pkg.dev/horology-dev/mcp-servers/document-graph@sha256:2848a2e168109efbecccbfad7f4fa5f21f900e1fde2da4ddd0ba66495f388a3a`

Build-ID and latest tags were published. No deployment, production migration, secret-policy update, plugin publication or scheduled-agent test was performed. The live gateway remains on its previous image/policy. The later gateway rollout requires the client-identity column migration and updated shared-access policy/OAuth environment, preserving spending history and existing OAuth grants; verify revocation during that release.
