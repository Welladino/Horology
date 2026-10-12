# Cloud Build release checks and consent presentation

Date: 2026-10-12

## Decision

Build release images from manually uploaded local source in Cloud Build. GitHub remains version control; no GitHub deployment trigger or branch protection is required. Preserve one local latest tag per MCP server. Artifact Registry retains five recent versions per package and protects deployed versions.

The consent page shows the signed-in identity, requesting client and readable permission groups. Technical tool names remain available in an expandable list. Presentation changes preserve cookie checks, single-use consent and the exact callback-origin CSP exception; no external assets, scripts or additional Google scopes.

## Checklist

- [x] Add source upload allowlist, build pipeline, disposable database tests, dependency and image/secret/config scans.
- [x] Add cleanup policy and deployment instructions.
- [x] Add consent layout and escaping/CSP regression coverage.
- [x] Run the new pipeline in Cloud Build and record its build ID.
- [x] Protect currently deployed image digests and activate Artifact Registry retention.
- [x] Deploy the updated consent page; verify its layout locally, image assets, OAuth regressions and existing authenticated client access.

The operator approved reporting unfixed image vulnerabilities while blocking High/Critical vulnerabilities with available fixes. Secret/misconfiguration scans and auth/quota tests remain blocking. Both runtime images use UID 10001 and omit unused pip/setuptools/wheel.

Deployment credentials were refreshed and Cloud Build enabled. The private source bucket has a seven-day lifecycle; the build account can read it, write build logs and publish only to the MCP repository. Artifact Registry retention is active after protecting both current deployed digests.

## Later

- [ ] Verify unattended access in the actual scheduled-agent runtime, including token refresh and timeouts.
- [ ] Separate login identity from per-run assignments/quotas; enforce fresh run limits without reconnecting.

These are tracked but not implemented by this change. See the existing GCP MCP deployment plan for the broader checklist.

## Verification

- Full local suite: **78 passed**. An initial Hermes dashboard startup race failed one check; the stable-stack rerun passed all tests.
- Cloud Build: **69 passed, 9 expected local Hermes stack skips**. Unexpected skips fail the pipeline. Disposable PostgreSQL exercises the quota/OAuth migrations and restricted-role, concurrency, quota and replay boundaries; no production migrations or paid calls.
- Source secret/Dockerfile configuration scans, all three pip audits, both image runtime contracts and blocking image scans passed.
- Debian image scans report **44 unfixed High findings per image**, zero Critical findings. They remain visible in build logs under the operator-approved policy. Review updated base images regularly; this is not a clean bill of security.
- Successful build: [f4825b13-97d6-48f4-9215-62d271d23778](https://console.cloud.google.com/cloud-build/builds;region=us-central1/f4825b13-97d6-48f4-9215-62d271d23778?project=horology-dev). Duration about 2m20s, region us-central1.
- Gateway revision: `mcp-gateway-00007-r2c`, digest `sha256:faf5e1ef426684baa4bbb4bbe6468643082f9291c3eca2a2cd971a9c7a885ef5`.
- Document graph revision: `document-graph-00002-rks`, digest `sha256:81c61b59660cb8e59a96ed22a35a2d6b208d2332c90cf6bbd859729e267f7d9f`.
- OAuth discovery returns 200; gateway anonymous/invalid bearer calls return 401; document-graph anonymous ingress returns 403. Native Codex `gateway_status` succeeds using its existing Google OAuth connection.
- Both deployed digests are tagged `deployed-current`; live cleanup policy was read back and verified. Deletion runs asynchronously, not at submission time.
- Old local cloud-release tags and the obsolete github-monitor image were removed. Active local MCP images retain only their Compose `latest` tags. Disposable test DB and preview server were removed/stopped.

## Follow-up security maintenance

- [ ] Review reported unfixed Debian findings as fixes/base-image updates become available.
- [ ] Update the pinned Trivy version deliberately and retest release gates.

No commit or push was performed. A real Google login through the newly styled page can be checked on the next reconnect; it is not required to keep an existing connection working.
