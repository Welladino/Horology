# Multi-page sites and dashboards on private Pages

## Topic
- multipage-pages-publishing

## Context
- Pipeline item 66 (HOR-9), rescoped by the founder on 04/11/2026: agents should be able to publish HTML pages, multi-page sites and dashboards to the workspace's private Cloudflare Pages project, not only the Stage 4 synthesis.
- Before this change `publish_synthesis` took one `index.html` plus up to 24 image or CSS files (8 MiB, 2 MiB HTML), always deployed to branch `pipeline-<ID>`, and only `horology-synthesis-artifacts` described it.
- Split off: Drive-only Research Links (item 68), Stage 1 document and Stage 4 report on both routes (item 69), a Pages URL tab (item 70). Digests stay Google Docs; weekly watchers are a later item; claude.ai Artifacts are out of scope.

## Decision
- **Extend the existing tool; no new tool.** `publish_synthesis` keeps its name, so the policy files, the `gateway_status` list, the consent check and every connector's approval stay as they are.
- **File types:** extra `.html` pages, `.js` and `.json` are allowed beside CSS and images. Up to 64 extra files, 8 MiB in all; `index.html` and each `.html`, `.js` or `.json` file at most 2 MiB. CSS and image limits are unchanged.
- **Pages control files refused:** any path whose first part starts with `_` (`_worker.js`, `_headers`, `_redirects`, `_routes.json`) or is `functions/`. With `.js` allowed this keeps an upload from turning into Pages Functions or changing headers and redirects; with Direct Upload these are normally separate form fields, so this is defence in depth.
- **Optional `page` name:** no name publishes to `pipeline-<ID>` as before (the Stage 4 synthesis). A name publishes to `pipeline-<ID>-<page>`: lowercase letters and digits with single hyphens, whole alias at most 28 characters, because Cloudflare truncates longer branch aliases and two names could then share one URL. The name is checked before the reservation, so a bad name spends nothing. The result now includes `branch`.
- **Access unchanged.** Every branch is a preview alias under `*.<project>.pages.dev`, which the existing preview Access application already protects; `protection.ensure_private` still checks both applications' exact-email rules before every upload.
- **Skill guidance in `horology-mcp-access`** (any skill using the gateway), not in the synthesis skill: when a page fits, the call, types, limits, page names, self-contained pages (local libraries, no trackers or outside calls), checks and the Drive record. `horology-synthesis-artifacts` is unchanged; its `visuals-and-pages.md` still describes the synthesis case correctly and item 70 is editing it.

## Rationale
- A new tool (for example `publish_page`) would need a policy change in both policy files, a consent and smoke-test update and a fresh connector approval for one parameter's worth of behaviour.
- Raising the 8 MiB total was not needed: files travel base64-encoded inside an MCP tool argument, so agent uploads are far smaller in practice.
- A content security policy that blocks outside scripts was considered and left out: it needs a `_headers` file the gateway would have to write, and it would decide for the founder whether dashboards may load CDN libraries. The skill asks for local files instead.

## Impact
- Files: `mcp-servers/mcp-gateway/integrations/cloudflare/client.py` and `tools.py`, `shared/consent.py` (consent wording), `tests/unit/mcp_servers/gateway/test_cloudflare_publish.py`, `docs/architecture/mcp/gateway.md`, `plugins/horology-tools/skills/horology-mcp-access/SKILL.md` and the horology-tools Codex plugin version 1.0.2.
- Nothing changes until the gateway is redeployed and the horology-tools skill is uploaded. Refused input still reaches the agent only as `permission_denied` (the shared error handling hides the reason), so the skill lists the limits.

## Follow-Ups
- Founder: redeploy the gateway, upload horology-tools, then publish one test site with a page name and check that the alias asks for sign-in without an Access session.
- The 28-character alias rule is from Cloudflare's preview-deployment documentation and has not been checked hands-on.
- Item 70 (Pages tab) can list these `pipeline-<ID>-<page>` URLs as well as the synthesis ones.
