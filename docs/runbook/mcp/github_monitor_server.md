# GitHub Monitor MCP Server

A small, purpose-built MCP server exposing eight read-only operations against exactly one repository (`Article_aggregator_agent`) — no arbitrary API access, no write capability anywhere. Follows the same narrow-tool, own-container, own-credential pattern as the [document graph MCP server](document_graph_server.md). See [`docs/planning/notes/2026-08-06_github-monitor-mcp-server_note.md`](../../planning/notes/2026-08-06_github-monitor-mcp-server_note.md) for the full rationale, and [`docs/planning/notes/2026-08-06_hardening-config-audit_note.md`](../../planning/notes/2026-08-06_hardening-config-audit_note.md) for why Hermes's own bundled `github-*` skills were rejected in favor of building this.

## What it exposes

- `get_repo_status()` — open PR/issue count, default branch, last push time.
- `list_recent_commits(limit?)` — recent commit history.
- `get_ci_status(ref?)` — latest GitHub Actions run status for a branch.
- `list_open_pull_requests()` — open PRs: number, title, author, files changed, created date.
- `list_dependabot_alerts(state?)` — security vulnerability alerts, by severity.
- `search_code(query)` — code search, scoped to this one repo only.
- `get_pull_request_diff(pr_number)` — **sends real source code (a diff) into the calling agent's context.**
- `get_file_content(path, ref?)` — **sends real source code (a file) into the calling agent's context.**

The last two are a deliberate exception to "no code content leaves the repo" — accepted so the eventual reviewing subagent can give specific feedback, not just status summaries. Don't add a similar content-fetching tool to a future MCP server without the same explicit tradeoff conversation.

## Credential

A GitHub **Fine-Grained Personal Access Token**, scoped to exactly the `Article_aggregator_agent` repository, with `Contents / Issues / Pull requests / Actions / Dependabot alerts` all set to **Read-only** and everything else at **No access**. No write permission anywhere — this token cannot create PRs, comments, issues, or push, even if asked.

`GITHUB_TOKEN` and `GITHUB_REPO` live only in this container's own environment (`github-monitor-mcp` service in `docker-compose.yml`) — never in Hermes's own environment.

If you ever need a permission this token doesn't have (e.g. `list_dependabot_alerts` initially failed with a 403), check whether GitHub has a **dedicated fine-grained permission** for it before reaching for a broader classic token — Dependabot alerts, for example, needed its own "Dependabot alerts: Read-only" permission, separate from Contents/Issues/PRs/Actions, added to the same token without widening its scope.

## Running it

Service `github-monitor-mcp` in `docker-compose.yml`, built from `mcp-servers/github-monitor/`. `streamable-http` transport on port `8766`, **not published to the host** — same isolation pattern as the document graph server.

```bash
docker compose build github-monitor-mcp
docker compose up -d github-monitor-mcp
```

## Testing it directly

```bash
# Not reachable from the host (should fail to connect):
curl -sS http://localhost:8766/mcp

# Reachable from Hermes's container:
docker exec horology-hermes curl -sS -o /dev/null -w "%{http_code}\n" http://github-monitor-mcp:8766/mcp
```

## Connecting a profile to it

```bash
printf "n\ny\n" | docker exec -i horology-hermes hermes mcp add github-monitor --url http://github-monitor-mcp:8766/mcp
# or, for a specific subagent profile:
printf "n\ny\n" | docker exec -i horology-hermes hermes -p <profile> mcp add github-monitor --url http://github-monitor-mcp:8766/mcp
```

Currently connected to Second-Soul and to `code-sentinel` (see `personas/subagents/code-sentinel.md`).

## Verifying the token is correctly scoped before connecting it to anything

Worth doing before wiring a new credential into the system — confirm it can read the intended repo and confirm it *cannot* read anything else:

```python
import httpx
token = "..."
headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
httpx.get("https://api.github.com/repos/Welladino/Article_aggregator_agent", headers=headers)  # expect 200
httpx.get("https://api.github.com/repos/Welladino/SomeOtherRepo", headers=headers)  # expect 404, not 401/403 - confirms scoping, not just auth failure
```
