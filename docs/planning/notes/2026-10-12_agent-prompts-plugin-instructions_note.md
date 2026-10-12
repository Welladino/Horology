# Agent prompt sources and Horology plugin operating skill

Date: 2026-10-12

## Completed

- Preserved both Agent Register Master Instructions / Prompt values exactly in `personas/subagents/research.md` and `technical-assessment.md`, with register IDs and platform/skill context.
- Updated persona index to distinguish these subscription agents from existing Hermes profiles; existing Hermes persona content was not replaced or synced into runtime.
- Changed only Master `H1:H3` to `Prompt source / link` and repository paths, with notes that GitHub links are pending publication. Operator explicitly chose to add links later. Native Sheets formatting and neighboring content are preserved; the header and both paths were visually checked in Google Sheets.
- Added `horology-mcp-access` to the existing private personal Horology plugin, version 1.0.1. App ID, connection, name, presentation and default prompt remain unchanged. Portable root manifest and compatible legacy manifest are preserved in repo source.
- Published release `pluginrel_6accb189d62c819193ed45f45f6ab880`; exact skill and App binding readback verified. The bundled skill validator and portable manifest schema validation passed. Existing authenticated `gateway_status` succeeds; no paid provider tool was called. Automatic skill loading in a refreshed ChatGPT/Codex host has not been behaviorally tested.

See [maintenance runbook](../../runbook/subscription-agents/horology_plugin.md). The local commit includes the accumulated authorized MCP cloud/OAuth, CI, IAM and local Compose/documentation work. No push is requested.

## Later exploration — not implemented

- [ ] Add other currently disabled MCP capabilities from the Agent Register after reviewing permissions and budgets.
- [ ] Plan document-graph MCP access for the intended external AI clients and runtimes.
- [ ] Decide Document Index graph-inclusion column(s), required metadata and how document-graph should handle that logic.
- [ ] Review unfixed Debian findings when fixes/base-image updates become available.
- [ ] Deliberately update pinned Trivy and retest release gates.
- [ ] Verify unattended access in the actual scheduled-agent runtime, including token refresh and timeouts.
- [ ] Separate identity from per-run assignments/quotas; enforce fresh run limits without reconnecting.
- [ ] Add clickable GitHub prompt links to Agent Register after publishing the persona files.
