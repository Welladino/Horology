# Hermes hardening: ports, egress, toolsets and isolation

## Topic
- hermes-hardening

## Context

Once the Hermes container was running (2026-08-05), the setup was reviewed for security gaps before adding skills, cron jobs and more provider keys. A wider audit followed on 2026-08-06 across cost caps, fallback model, integrations, toolsets and filesystem isolation; findings are in the [hardening research brief](../research/2026-08-06_hardening-config-options_research.md).

## Decisions

**Ports bound to localhost (2026-08-05).** Compose published `8642:8642` and `9119:9119`, which Docker binds to `0.0.0.0`, reachable from the local network; 8642 (the OpenAI-compatible API) has no authentication. Both are now `127.0.0.1:` only, checked with `docker port horology-hermes`. They don't clash with `Article_aggregator_agent`'s dev ports: collisions are per port, not per address.

**Egress firewall on (2026-08-05).** Hermes' optional iron-proxy (`hermes egress install`, `setup`, `start`) intercepts outbound TLS, swaps opaque proxy tokens for real keys only at the network edge so the agent's context never holds raw keys, and allowlists outbound domains (anything else gets a 403 before bytes leave). It was enabled early because autonomous web research makes prompt-injected exfiltration a real risk, and retrofitting after more keys and cron jobs would be harder. The OpenRouter key was minted into a proxy token for `openrouter.ai`; a live `hermes chat -q` confirmed model calls work through it. New provider keys go through `hermes egress setup` rather than sitting as bare environment variables.

**Hermes' own databases don't replace Neon (2026-08-05).** `state.db`, `kanban.db` and `projects.db` are SQLite files owned by Hermes holding conversation and operational state. They are single-machine and schema-owned by Hermes, so the document graph stays a separate Postgres store.

**Toolsets trimmed and a fallback model set (2026-08-06).** `computer_use`, `image_gen`, `video_gen`, `video`, `bfl`, `vision`, `homeassistant`, `spotify`, `yuanbao`, `tts`, `stt` and `x_search` were disabled on every profile; `code_execution`, `terminal`, `delegation` and `cronjob` also on the subagents. A live query confirmed `gtm-manager` still worked. The fallback model is `z-ai/glm-5.2` through OpenRouter (`hermes config set fallback_model.*`, confirmed with `hermes fallback list`). Hermes has no token or cost cap, so that belongs on the OpenRouter dashboard.

**Filesystem isolation confirmed, not changed (2026-08-06).** `docker inspect` showed Hermes has exactly one mount (`hermes-data/` → `/opt/data`), the MCP containers none, nothing privileged, no added capabilities, an isolated network and an authenticated dashboard. Containers can't reach the founder's home directory or other repositories. The first `hermes security audit` found three HIGH vulnerabilities in bundled `aiohttp==3.14.1` and `cryptography==48.0.1`; `hermes doctor --fix` fixed one of five flagged issues.

## Rationale

Keep the blast radius of any one credential or exposure small, and verify each claim (port binding, proxy working, what a database holds) on the live system instead of trusting docs or one command's output. The audit found several first-pass claims that needed correcting this way, such as direct `config.yaml` edits being silently reverted.

## Impact

- Hermes is reachable only from the laptop, holds no raw provider keys, and can reach only allowlisted domains.
- Every profile has a far smaller tool surface than Hermes' defaults. Current inventory: [Hermes architecture](../../architecture/hermes/hermes-agents.md#tools-and-limits).

## Follow-Ups

- Set a spend cap on the OpenRouter account.
- Track the `aiohttp` and `cryptography` findings in the upstream `nousresearch/hermes-agent` image.
- Decide whether `API_SERVER_ENABLED` should ever be on for this project.
