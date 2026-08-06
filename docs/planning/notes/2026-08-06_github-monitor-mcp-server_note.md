# Implementation Note

## Topic
- github-monitor-mcp-server

## Context

First of the three (c) integrations scoped this session: GCP for a DevOps agent, Supabase for a DB agent, GitHub for code quality/test/security monitoring. Decided (with the founder) to build one combined DevOps/Infra subagent covering all three later, and to build GitHub first since it needed no cloud IAM setup and reused patterns already proven (the document-graph MCP server's narrow-tool, own-container, own-credential design).

Also decided against Hermes's own bundled GitHub skills (`github-auth`, `github-pr-workflow`, etc., seen in the skill catalog and removed from both subagent profiles during the earlier hardening pass) — those authenticate via `gh`/`git` CLI executed through `terminal`/`code_execution`, which is the same "broad shell access with a credential in scope" pattern already rejected once this session (the original code-execution-based `write-document` skill). A purpose-built MCP server with named, read-only tools keeps the same narrow-capability principle used for the document graph.

## Decision

**Credential**: a GitHub Fine-Grained Personal Access Token, scoped to exactly one repo (`Article_aggregator_agent`), with `Contents / Issues / Pull requests / Actions` set to Read-only and everything else at No access — explicitly no write access anywhere, per the founder's requirement that it must not be able to create PRs. Verified working and correctly scoped via a direct API test before building anything on top of it (confirmed it can read `Article_aggregator_agent`, confirmed a 404 — not 401/403 — when probing a repo outside its scope, i.e. it's authenticated but correctly can't see anything else).

**Server**: `mcp-servers/github-monitor/` (Python, same `mcp` SDK, same `streamable-http`-on-internal-network-only pattern as `document-graph-mcp`, no host port published). Eight tools:
- `get_repo_status`, `list_recent_commits`, `get_ci_status`, `list_open_pull_requests`, `list_dependabot_alerts`, `search_code` — metadata/status-level, no code content.
- `get_pull_request_diff`, `get_file_content` — added after an explicit tradeoff discussion with the founder: these send actual source code into the calling agent's context (and from there, through OpenRouter to whichever model is reasoning about it). Accepted deliberately, not a default — the founder chose to include them so the eventual DevOps subagent can give specific code-quality feedback, not just repo-health status.

**Dependabot alerts needed a permission not in the original four.** First test returned `403 Forbidden`; Second-Soul's own suggestion (switch to a classic token with broad `repo`/`security_events` scope) was correctly rejected — that would have undone the narrow-scoping this whole session has been built around. The actual fix, found via a targeted search rather than accepting the broad-scope suggestion: fine-grained tokens have a **separate, dedicated "Dependabot alerts: Read-only" permission**, distinct from Contents/Issues/PRs/Actions. Added it to the existing token (no new token needed); retested and confirmed working — the tool now returns real, substantive results (currently ~14 Pillow alerts, 3 cryptography, 3 aiohttp, etc. on `Article_aggregator_agent`).

**Connected to Second-Soul only, for now** — no dedicated DevOps subagent persona exists yet (planned as the next step, combining GitHub + GCP + Supabase into one persona per the founder's earlier decision). Verified end-to-end with real queries through Second-Soul: `get_repo_status` (accurate real data: 0 open PRs/issues, correct last-push time) and `list_dependabot_alerts` (real, actionable vulnerability data).

## Rationale

Same principle as every prior integration this session: narrowest justified capability, verify the credential and the tool surface independently before connecting them to an agent, and when a permission gap appears, look for the narrow fix (a specific fine-grained permission) before accepting a broad one (a classic token) — even when the broad fix is what the agent itself suggests.

## Impact

- `Article_aggregator_agent`'s CI status, PR activity, commit history, and Dependabot security alerts are now queryable by any Hermes profile connected to this MCP server.
- The `get_pull_request_diff`/`get_file_content` tools are a deliberate, named exception to "no code content leaves the repo" — worth remembering as the boundary if a future integration is tempted to add similar content-fetching tools without the same explicit tradeoff conversation.
- `.env` / `.env.example` now document `GITHUB_TOKEN` and `GITHUB_REPO` alongside the Neon variables.

## Follow-Ups

- Build the combined DevOps/Infra subagent persona and connect this server (plus the future GCP and Supabase integrations) to it, rather than leaving GitHub monitoring only reachable by Second-Soul directly.
- Scope and build the GCP integration (service account, least-privilege IAM roles — likely `roles/logging.viewer` per the earlier founding-decisions note) and the Supabase integration (a read-only role on the NLE project) next.
- Consider whether `get_pull_request_diff`/`get_file_content` should be gated behind an explicit persona instruction ("only fetch content when metadata isn't enough") once the DevOps subagent exists, so it doesn't default to pulling full diffs for routine status checks.
