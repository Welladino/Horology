# Implementation Note

## Topic
- hardening-config-audit

## Context

Research and findings across six configuration/security areas (token cap, fallback model, external integrations, toolset scope, filesystem/auth isolation) are in [`docs/planning/research/2026-08-06_hardening-config-options_research.md`](../research/2026-08-06_hardening-config-options_research.md). This note captures only what was actually decided and implemented.

## Decision

**(a) Token/cost cap**: not implementable in Hermes itself — set directly on the OpenRouter account dashboard instead. Not done as part of this pass (founder action, outside this repo).

**(b) Fallback model**: set to `z-ai/glm-5.2` via OpenRouter, using `hermes config set fallback_model.provider/.model` (CLI command, not a direct file edit). Confirmed active via `hermes fallback list`: primary `deepseek/deepseek-v4-flash`, fallback `z-ai/glm-5.2`.

**(c) GCP / Supabase / GitHub integrations**: deferred, not done in this pass — scoped as its own follow-on piece of work (later became the GitHub monitoring MCP server and Code Sentinel subagent).

**(d) Disabled unnecessary toolsets, across all three profiles at the time (default/Second-Soul, gtm-manager, marketing-executive):**
- `computer_use, image_gen, video_gen, video, bfl, vision, homeassistant, spotify, yuanbao, tts, stt, x_search` — disabled everywhere.
- `code_execution, terminal, delegation, cronjob` — additionally disabled on `gtm-manager` and `marketing-executive` only (kept on Second-Soul), matching each subagent's persona-stated boundary of not delegating and not needing code/shell execution for their actual work.
- Verified `gtm-manager` still functions correctly after the trim via a live chat query — remaining tools (web, browser, file, skills, todo, memory, session_search, clarify) plus document-graph MCP tools confirmed intact.

**(e) Filesystem isolation and auth**: verified already correct via direct inspection, no changes needed (single bind mount, not privileged, no added capabilities, isolated network, dashboard auth-gated, unused API port confirmed not listening). Ran `hermes security audit` for the first time — found 3 real HIGH-severity vulnerabilities in bundled dependencies (`aiohttp==3.14.1`, `cryptography==48.0.1`), tracked as a follow-up, not fixed in this pass. `hermes doctor --fix` resolved 1 of 5 flagged issues automatically.

## Rationale

Narrowest justified capability per identity, verified directly rather than trusted from documentation or a single command's output — see the research brief for the specific cases where a first-pass claim (the `fallback_model` warning, the assumption that direct file edits work) turned out to need correction against live behavior.

## Impact

- All three profiles at the time had a meaningfully smaller tool surface than Hermes's defaults, with subagent profiles specifically stripped of code execution and shell access.
- Confirmed, not just assumed, that container-level filesystem isolation already satisfied "no access to other folders."
- Real, actionable vulnerability findings (3 HIGH in aiohttp/cryptography) now on record.

## Follow-Ups

- Set an actual spend cap on the OpenRouter account dashboard — not done here.
- Scope and design (c) as its own piece of work — later addressed by the GitHub monitoring MCP server and Code Sentinel subagent; GCP and Supabase integrations still outstanding.
- Track the aiohttp/cryptography vulnerabilities — check for an updated `nousresearch/hermes-agent` image, or investigate manual remediation.
- Consider whether `API_SERVER_ENABLED` should ever be turned on for this project at all.
