"""MCP server exposing read-only GitHub monitoring tools against exactly one
repo (GITHUB_REPO, e.g. "Welladino/Article_aggregator_agent") for code
quality, test, and security signal-watching.

No write access anywhere - the underlying PAT is a fine-grained,
read-only, single-repo token (Contents/Issues/PRs/Actions: Read-only,
everything else: No access). This server cannot create PRs, comments,
issues, or push anything, even if asked - GitHub's own token scope
would reject any write call regardless of what this code does.

The GitHub token lives only in this process's environment - never in
Hermes's environment, never visible to whatever calls these tools.
"""
import os

import httpx
from mcp.server.mcpserver import MCPServer

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not set in this server's environment.")

GITHUB_REPO = os.environ.get("GITHUB_REPO")
if not GITHUB_REPO:
    raise RuntimeError("GITHUB_REPO is not set (e.g. 'Welladino/Article_aggregator_agent').")

API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

mcp = MCPServer("horology-github-monitor")


def _get(path: str, params: dict | None = None) -> dict | list:
    resp = httpx.get(f"{API_BASE}{path}", headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def get_repo_status() -> dict:
    """High-level snapshot of the monitored repo: open PR count, open issue
    count, default branch, and latest push time."""
    repo = _get(f"/repos/{GITHUB_REPO}")
    open_prs = _get(f"/repos/{GITHUB_REPO}/pulls", params={"state": "open", "per_page": 1})
    open_issues_count = repo.get("open_issues_count", 0)
    return {
        "repo": repo.get("full_name"),
        "default_branch": repo.get("default_branch"),
        "pushed_at": repo.get("pushed_at"),
        "open_issue_and_pr_count": open_issues_count,
        "has_open_prs": len(open_prs) > 0,
    }


@mcp.tool()
def list_recent_commits(limit: int = 10) -> list[dict]:
    """List recent commits on the default branch: sha, author, date, message."""
    limit = max(1, min(limit, 50))
    commits = _get(f"/repos/{GITHUB_REPO}/commits", params={"per_page": limit})
    return [
        {
            "sha": c["sha"][:12],
            "author": (c.get("commit", {}).get("author") or {}).get("name"),
            "date": (c.get("commit", {}).get("author") or {}).get("date"),
            "message": (c.get("commit", {}).get("message") or "").split("\n")[0],
        }
        for c in commits
    ]


@mcp.tool()
def get_ci_status(ref: str | None = None) -> dict:
    """Latest GitHub Actions workflow run status for a branch/ref (default:
    the repo's default branch)."""
    branch = ref or _get(f"/repos/{GITHUB_REPO}")["default_branch"]
    runs = _get(
        f"/repos/{GITHUB_REPO}/actions/runs",
        params={"branch": branch, "per_page": 1},
    )
    workflow_runs = runs.get("workflow_runs", [])
    if not workflow_runs:
        return {"branch": branch, "status": "no_runs_found"}
    run = workflow_runs[0]
    return {
        "branch": branch,
        "workflow": run.get("name"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "run_started_at": run.get("run_started_at"),
        "html_url": run.get("html_url"),
    }


@mcp.tool()
def list_open_pull_requests() -> list[dict]:
    """List open pull requests: number, title, author, files changed count,
    created date, CI status is NOT included here - use get_ci_status separately."""
    prs = _get(f"/repos/{GITHUB_REPO}/pulls", params={"state": "open", "per_page": 30})
    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "author": pr.get("user", {}).get("login"),
            "created_at": pr.get("created_at"),
            "changed_files": pr.get("changed_files"),
            "base": pr.get("base", {}).get("ref"),
            "head": pr.get("head", {}).get("ref"),
        }
        for pr in prs
    ]


@mcp.tool()
def get_pull_request_diff(pr_number: int) -> str:
    """Fetch the unified diff for a specific pull request. This sends the
    actual code changes to the calling agent's context - use only when
    metadata (list_open_pull_requests) isn't enough to form an opinion."""
    resp = httpx.get(
        f"{API_BASE}/repos/{GITHUB_REPO}/pulls/{pr_number}",
        headers={**HEADERS, "Accept": "application/vnd.github.v3.diff"},
        timeout=30,
    )
    resp.raise_for_status()
    diff = resp.text
    max_chars = 40000
    if len(diff) > max_chars:
        diff = diff[:max_chars] + f"\n\n... [truncated, diff was {len(diff)} chars]"
    return diff


@mcp.tool()
def get_file_content(path: str, ref: str | None = None) -> str:
    """Fetch the content of a single file at a given ref (default: default
    branch). Sends actual source code to the calling agent's context."""
    branch = ref or _get(f"/repos/{GITHUB_REPO}")["default_branch"]
    import base64

    data = _get(f"/repos/{GITHUB_REPO}/contents/{path}", params={"ref": branch})
    if isinstance(data, list):
        raise ValueError(f"{path} is a directory, not a file")
    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    max_chars = 40000
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n... [truncated, file was {len(content)} chars]"
    return content


@mcp.tool()
def list_dependabot_alerts(state: str = "open") -> list[dict]:
    """List Dependabot security alerts for the repo. state: open|fixed|dismissed."""
    alerts = _get(
        f"/repos/{GITHUB_REPO}/dependabot/alerts",
        params={"state": state, "per_page": 30},
    )
    return [
        {
            "number": a["number"],
            "severity": a.get("security_advisory", {}).get("severity"),
            "summary": a.get("security_advisory", {}).get("summary"),
            "package": a.get("dependency", {}).get("package", {}).get("name"),
            "state": a.get("state"),
        }
        for a in alerts
    ]


@mcp.tool()
def search_code(query: str) -> list[dict]:
    """Search code within the monitored repo only (query is automatically
    scoped with repo:<GITHUB_REPO>)."""
    results = _get(
        "/search/code",
        params={"q": f"{query} repo:{GITHUB_REPO}", "per_page": 20},
    )
    return [
        {"path": item["path"], "name": item["name"], "html_url": item["html_url"]}
        for item in results.get("items", [])
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8766)
