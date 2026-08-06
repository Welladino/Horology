# Research Brief

## Topic
- hardening-config-options

## Question
- Before adding more capability to Horology, what configuration/security areas need attention: is there a token/cost cap available in Hermes, how should the fallback model be configured, what toolsets should be disabled for a text-only business co-founder system, and is the current filesystem/auth isolation actually as safe as assumed?

## Summary
- Hermes has no dollar or token spend cap — only `agent.max_turns` (iteration count, not cost). Real cost control must happen on OpenRouter's own dashboard.
- The `fallback_model` config key works but the CLI's dot-notation validator incorrectly flags it as unrecognized, suggesting `fallback_providers` instead — worth checking the runtime behavior (`hermes fallback list`) directly rather than trusting the warning.
- Editing `config.yaml` on disk directly while Hermes's gateway is running is unreliable — the live process holds its own in-memory config and can revert external edits.
- `computer_use` is real, unsandboxed desktop control; `code_execution`/`terminal` on the local backend are not sandboxed either (share the container's own kernel, only secret-shaped env vars are stripped) — neither has legitimate use for research/writing subagents.
- Container-level filesystem isolation was already correct by original design (single bind mount, no host access) — verified directly, not just assumed.
- `hermes security audit` (a built-in OSV.dev scanner, previously unused) found 3 real HIGH-severity vulnerabilities in bundled dependencies.

## Sources
- Two background research agents (Sonnet) tasked with: (1) Hermes token cap / fallback model config, via docs.hermes-agent.nousresearch.com and the FAQ; (2) Hermes toolset/skill disable options and what each toolset actually grants access to.
- Direct verification: `docker inspect` on both running containers (mounts, privilege, capabilities, network mode), `curl` tests against published ports, `hermes security audit`, `hermes doctor --fix`, `hermes fallback list`, `hermes config set` behavior tested live.

## Findings

**(a) Token/cost cap**: no dollar or token budget mechanism exists in Hermes. The only related control is `agent.max_turns` (default 500) — a hard stop on tool-call iterations per turn, not cost. Confirmed via Hermes's own FAQ, which states cost management is left to the provider.

**(b) Fallback model**: `hermes config set fallback_model.provider openrouter` / `.model z-ai/glm-5.2` produced a CLI warning ("not a recognized config key," suggesting `fallback_providers`), but `hermes fallback list` confirmed it was correctly parsed and active (primary `deepseek/deepseek-v4-flash`, fallback `z-ai/glm-5.2`, both via OpenRouter). The warning is about the dot-notation validator in `config set`, not the runtime parser. Separately found: a direct file edit to `config.yaml` (bypassing CLI commands) silently succeeded then got reverted — almost certainly the live gateway process persisting its own in-memory config over the external edit. CLI commands against the running process are the only reliable way to change config while Hermes is up.

**(d) Toolset scope, by capability**:
- `computer_use` — real, unsandboxed OS control (click/type/scroll across the desktop), no legitimate use for a text-only system.
- `code_execution`/`terminal` on local backend — **not sandboxed**: share the container's own kernel; only secret-shaped env vars (`KEY/TOKEN/SECRET/PASSWORD/CREDENTIAL/AUTH`) are stripped, otherwise real execution with a timeout/output cap, not containment.
- `image_gen, video_gen, video, bfl, vision, homeassistant, spotify, yuanbao, tts, stt, x_search` — no legitimate use for research/writing subagents.
- Tool/skill toggles are per-profile, not global to the gateway — confirmed via `hermes tools list` differing per `-p <profile>` invocation.
- `--safe-mode` is a troubleshooting flag (disables all customization to isolate bugs), not a capability-restriction/sandboxing feature.

**(e) Filesystem isolation and auth, verified directly**:
- `docker inspect` confirmed exactly one bind mount on the Hermes container (`Horology/hermes-data` → `/opt/data`) — no access to the founder's home directory or `Article_aggregator_agent`. `HERMES_WRITE_SAFE_ROOT=/opt/data` matches.
- Container not privileged, no added Linux capabilities, isolated Compose network (not host networking).
- Dashboard (port 9119) correctly returns a login redirect without credentials.
- API port 8642 (published, no auth by default per Hermes's docs) is not actually listening — `API_SERVER_ENABLED` was never set. Safe by omission, not by design — if ever enabled, `API_SERVER_KEY` must be set at the same time.
- `hermes security audit` found 3 real HIGH-severity vulnerabilities in bundled Python dependencies (`aiohttp==3.14.1`, `cryptography==48.0.1`), with fixed versions available upstream. `hermes doctor --fix` resolved 1 of 5 flagged issues automatically; the dependency vulnerabilities need either an upstream image update or manual intervention.

## Recommendation
- Set a spend cap directly on the OpenRouter account dashboard; don't try to work around the missing Hermes-side mechanism.
- Keep the fallback model set via CLI commands (not direct file edits), and treat `hermes fallback list`/similar CLI-state commands as the source of truth over static config warnings.
- Disable `computer_use, image_gen, video_gen, video, bfl, vision, homeassistant, spotify, yuanbao, tts, stt, x_search` on every profile; additionally disable `code_execution, terminal, delegation, cronjob` on subagent profiles specifically (keep on the supervisor).
- Treat GCP/Supabase/GitHub integrations as a separate, deliberately-scoped piece of work rather than rushing them into this pass.
- Track the aiohttp/cryptography vulnerabilities for a future fix; leave `API_SERVER_ENABLED` off unless there's a concrete need for it.

## Open Questions
- Whether an updated `nousresearch/hermes-agent` image will bundle fixed dependency versions, or whether manual remediation will be needed.
- Whether `API_SERVER_ENABLED` will ever be needed for this project at all.
