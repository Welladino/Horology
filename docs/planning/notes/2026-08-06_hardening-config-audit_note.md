# Implementation Note

## Topic
- hardening-config-audit

## Context

A deliberate pass through six configuration/security areas before adding more capability to the system: token/cost cap, fallback model, external integrations (GCP/Supabase/GitHub), disabling unused toolsets, filesystem/auth isolation, and anything else worth checking. Used two background research agents (sonnet) for doc-research questions (a/b/d) while directly verifying container isolation and running config myself (c is deferred, e is hands-on).

## Decision

**(a) Token/cost cap: no such mechanism exists in Hermes.** Confirmed via docs and Hermes's own FAQ: there is no dollar or token budget. The only related control is `agent.max_turns` (default 500, a hard stop on tool-call iterations per turn, not cost). Real cost control has to happen on OpenRouter's own dashboard (spend limits/alerts) — decided not to try to work around this in Hermes; set the cap at the provider level instead. Not yet done — founder to configure directly on OpenRouter.

**(b) Fallback model set to z-ai/glm-5.2, confirmed working.** Set via `hermes config set fallback_model.provider openrouter` / `hermes config set fallback_model.model z-ai/glm-5.2` — despite a CLI warning that `fallback_model.provider`/`.model` "is not a recognized config key" (suggesting `fallback_providers` instead), `hermes fallback list` confirmed it was correctly parsed and active: primary `deepseek/deepseek-v4-flash`, fallback chain `z-ai/glm-5.2`, both via OpenRouter. The warning appears to be about the dot-notation validator in `config set`, not the runtime parser — the legacy key still works. Also found and worth remembering: **editing `config.yaml` directly on disk while the gateway is running is unreliable** — a first attempt via direct file edit (Python script) silently succeeded then got reverted, almost certainly because the live gateway process holds its own in-memory config and periodically persists it, clobbering external edits. Always use `hermes config set` / `hermes fallback add` / equivalent CLI commands against the running process, never edit `config.yaml` on disk directly while Hermes is up.

**(c) GCP / Supabase / GitHub integrations: deferred, not done in this pass.** Scoped as its own follow-on piece of work — each needs a dedicated least-privilege credential, a decision on MCP server vs. other integration mechanism (matching the document-graph MCP server's narrow-tool-surface pattern, not a broad admin connection), and in most cases a DevOps/DB-engineer subagent persona that doesn't exist yet. Not attempted here to avoid rushing a real design decision.

**(d) Disabled unnecessary toolsets, across all three profiles (default/Second-Soul, gtm-manager, marketing-executive):**
- `computer_use, image_gen, video_gen, video, bfl, vision, homeassistant, spotify, yuanbao, tts, stt, x_search` — disabled everywhere. None of these have any legitimate use for a text-only business co-founder system; `computer_use` in particular is real, unsandboxed OS control (confirmed via research: click/type/scroll across the desktop, not contained).
- `code_execution, terminal, delegation, cronjob` — additionally disabled on `gtm-manager` and `marketing-executive` only (kept on Second-Soul). Research confirmed `code_execution`/`terminal` on the local backend are **not sandboxed** — they share the container's own kernel; only secret-shaped env vars (matching `KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH`) are stripped, otherwise it's real code execution with a timeout/output cap, not containment. Neither subagent's actual work (research, writing) needs to run code or shell commands. `delegation`/`cronjob` were disabled to match each subagent's own persona-stated boundary ("you do not have subagents of your own to delegate to") — previously stated as policy but not actually enforced at the tool level.
- Verified `gtm-manager` still functions correctly after the trim via a live chat query — confirmed its remaining tools (web, browser, file, skills, todo, memory, session_search, clarify) plus the document-graph MCP tools are intact and it correctly self-describes its scope.

**(e) Filesystem isolation and auth — verified already correct, no changes needed:**
- `docker inspect` confirms the Hermes container has exactly one bind mount (`Horology/hermes-data` → `/opt/data`) — no access to the founder's home directory, `Article_aggregator_agent`, or anything else on the host. `HERMES_WRITE_SAFE_ROOT=/opt/data` is also set, matching this.
- Container is not privileged, has no added Linux capabilities, and is on the isolated `horology_default` Compose network (not host networking).
- Dashboard (port 9119, host-published) correctly returns a login redirect (302) without credentials — basic auth is enforced, as set up earlier in the project.
- API port 8642 (host-published, no auth by default per Hermes's own docs) is confirmed **not actually listening** — `API_SERVER_ENABLED` was never set, so there's nothing to reach right now. This is safe by omission, not by design — flagged as a standing rule: if that API server is ever enabled in the future, `API_SERVER_KEY` must be set at the same time, or it becomes a real unauthenticated hole.
- `hermes security audit` (built-in OSV.dev supply-chain scanner) found 3 real HIGH-severity vulnerabilities in bundled Python dependencies (`aiohttp==3.14.1`, `cryptography==48.0.1`) with fixed versions available upstream (3.14.3, 50.0.0 respectively). These are in Hermes's own vendored environment, not something this project introduced. `hermes doctor --fix` resolved 1 of 5 flagged issues automatically; the dependency vulnerabilities require either an upstream Hermes image update or manual intervention — not fixed in this pass.
- Confirmed `--safe-mode` is a troubleshooting flag (disables all customization to isolate bugs), not a capability-restriction/sandboxing feature — ruled out as irrelevant to this hardening pass.

## Rationale

This pass followed the same principle applied throughout the project: narrowest justified capability per identity, verify claims directly rather than trust documentation or a single command's output at face value (the `config.yaml` direct-edit failure and the `fallback_model` key-name warning both would have been silently wrong conclusions without re-checking against `hermes fallback list`), and treat "safe because nothing bad has happened yet" (the unauthenticated API port) as different from "safe by design."

## Impact

- All three profiles now have a meaningfully smaller tool surface than Hermes's defaults, with the two subagent profiles specifically stripped of code execution and shell access, which they never needed.
- Confirmed, not just assumed, that container-level filesystem isolation already satisfies "no access to other folders" — this was already true structurally before this audit, from the original `docker-compose.yml` design.
- Real, actionable vulnerability findings (3 HIGH in aiohttp/cryptography) now on record, previously undiscovered.

## Follow-Ups

- Set an actual spend cap on the OpenRouter account dashboard (outside Hermes's own config) — not done here.
- Scope and design (c) — GCP/Supabase/GitHub integrations — as its own piece of work: credentials, MCP-vs-other-mechanism decision per integration, and the DevOps/DB-engineer subagent persona(s) that would use them.
- Track the aiohttp/cryptography vulnerabilities — check for an updated `nousresearch/hermes-agent` image that bundles fixed versions, or investigate manual remediation if no upstream fix lands soon.
- Consider whether `API_SERVER_ENABLED` should ever be turned on for this project at all — if there's no concrete need, leaving it off entirely (rather than "off but tracked as a future risk") may be simpler than remembering the `API_SERVER_KEY` requirement later.
