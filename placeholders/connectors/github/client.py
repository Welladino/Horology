"""Restricted github integration."""
import base64
import re
from urllib.parse import quote
from policy import Denied, credential
from shared.http import MAX_BYTES, request
from shared.text import clean_text


def repo_check(policy, config, repository):
    if repository not in policy['repositories'] or repository not in config.get('repositories', []):
        raise Denied('Repository is outside assignment scope')

async def github_file(policy, config, repository, path, ref):
    repo_check(policy, config, repository)
    if not path or path.startswith('/') or any(p in ('', '.', '..') for p in path.split('/')) or '\\' in path:
        raise Denied('Invalid repository path')
    if not ref or len(ref) > 200:
        raise Denied('A bounded explicit ref is required')
    data = await request('GET', f'https://api.github.com/repos/{repository}/contents/{quote(path, safe="/")}', token=credential('GITHUB_TOKEN'), params={'ref': ref})
    if not isinstance(data, dict) or data.get('type') != 'file' or data.get('encoding') != 'base64' or data.get('size', MAX_BYTES) > 40_000:
        raise Denied('Only individual files up to 40 KB are supported')
    return {'path': path, 'sha': data['sha'], 'content': clean_text(base64.b64decode(data['content']).decode('utf-8'), 40_000)}

async def github_records(policy, config, repository, kind, number):
    repo_check(policy, config, repository)
    endpoints = {'issues': 'issues', 'pull_requests': 'pulls', 'commits': 'commits', 'workflow_runs': 'actions/runs'}
    if kind not in endpoints or type(number) is not int or number < 0:
        raise Denied('Unsupported repository read')
    if number and kind not in ('issues', 'pull_requests'):
        raise Denied('Number applies only to issues and pull requests')
    endpoint = endpoints[kind] + (f'/{number}' if number else '')
    data = await request('GET', f'https://api.github.com/repos/{repository}/{endpoint}', token=credential('GITHUB_TOKEN'), params={'per_page': 10})
    if kind == 'workflow_runs':
        data = data.get('workflow_runs', [])
    records = data if isinstance(data, list) else [data]
    # Do not return CI logs, user profiles, raw credentials or arbitrary response fields.
    allowed = ('number', 'title', 'state', 'html_url', 'sha', 'status', 'conclusion', 'created_at', 'updated_at', 'body')
    return [{k: clean_text(item[k], 5000) for k in allowed if k in item} for item in records[:10]]

async def github_tree(policy, config, repository, ref):
    repo_check(policy, config, repository)
    if not ref or len(ref) > 200:
        raise Denied('An explicit bounded ref is required')
    data = await request('GET', f'https://api.github.com/repos/{repository}/git/trees/{quote(ref, safe="")}', token=credential('GITHUB_TOKEN'))
    return {'sha': data.get('sha'), 'truncated': data.get('truncated', False), 'entries': [{k: item[k] for k in ('path', 'type', 'sha', 'size') if k in item} for item in data.get('tree', [])[:200]]}

async def github_search(policy, config, repository, query):
    repo_check(policy, config, repository)
    if not re.fullmatch(r'[A-Za-z0-9_ .-]{1,200}', query) or not query.strip():
        raise Denied('Search accepts plain terms only; no qualifiers')
    data = await request('GET', 'https://api.github.com/search/code', token=credential('GITHUB_TOKEN'), params={'q': f'{query} repo:{repository}', 'per_page': 5})
    items = data.get('items', [])[:5]
    if any(item.get('repository', {}).get('full_name', '').lower() != repository.lower() for item in items):
        raise Denied('Provider search returned an unapproved repository')
    return [{'path': item['path'], 'sha': item['sha'], 'html_url': item['html_url']} for item in items]

async def github_pr_files(policy, config, repository, number):
    repo_check(policy, config, repository)
    if type(number) is not int or number < 1:
        raise Denied('Positive pull request number required')
    data = await request('GET', f'https://api.github.com/repos/{repository}/pulls/{number}/files', token=credential('GITHUB_TOKEN'), params={'per_page': 20})
    return [{k: clean_text(item[k], 2000) for k in ('filename', 'status', 'additions', 'deletions', 'patch') if k in item} for item in data[:20]]


async def _monitor_get(path, params=None):
    return await request("GET", "https://api.github.com" + path, token=credential("GITHUB_TOKEN"), params=params)


async def github_repo_status(policy, config, repository: str) -> dict:
    """High-level snapshot of the monitored repo: open PR count, open issue
    count, default branch, and latest push time."""
    repo_check(policy, config, repository)
    repo = await _monitor_get(f"/repos/{repository}")
    open_prs = await _monitor_get(f"/repos/{repository}/pulls", params={"state": "open", "per_page": 1})
    open_issues_count = repo.get("open_issues_count", 0)
    return {
        "repo": repo.get("full_name"),
        "default_branch": repo.get("default_branch"),
        "pushed_at": repo.get("pushed_at"),
        "open_issue_and_pr_count": open_issues_count,
        "has_open_prs": len(open_prs) > 0,
    }


async def github_recent_commits(policy, config, repository: str, limit: int = 10) -> list[dict]:
    """List recent commits on the default branch: sha, author, date, message."""
    repo_check(policy, config, repository)
    limit = max(1, min(limit, 50))
    commits = await _monitor_get(f"/repos/{repository}/commits", params={"per_page": limit})
    return [
        {
            "sha": c["sha"][:12],
            "author": (c.get("commit", {}).get("author") or {}).get("name"),
            "date": (c.get("commit", {}).get("author") or {}).get("date"),
            "message": (c.get("commit", {}).get("message") or "").split("\n")[0],
        }
        for c in commits
    ]


async def github_ci_status(policy, config, repository: str, ref: str | None = None) -> dict:
    """Latest GitHub Actions workflow run status for a branch/ref (default:
    the repo's default branch)."""
    repo_check(policy, config, repository)
    branch = ref or (await _monitor_get(f"/repos/{repository}"))["default_branch"]
    runs = await _monitor_get(
        f"/repos/{repository}/actions/runs",
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


async def github_dependabot_alerts(policy, config, repository: str, state: str = "open") -> list[dict]:
    """List Dependabot security alerts for the repo. state: open|fixed|dismissed."""
    repo_check(policy, config, repository)
    if state not in ('open', 'fixed', 'dismissed'):
        raise Denied('Unsupported alert state')
    alerts = await _monitor_get(
        f"/repos/{repository}/dependabot/alerts",
        params={"state": state, "per_page": 5},
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
