from horology_runtime.operations import observe
from shared.access import current_assignment
"""Register restricted github MCP tools."""
from . import client


def register_tools(mcp, access):
    policy, ledger = access.policy, access.ledger
    scope, reserve = access.scope, access.reserve

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_read_file(repository: str, path: str, ref: str) -> dict:
        """Read one allowlisted repository file at an explicit branch or commit."""
        assignment, config = scope('github_read_file')
        client.repo_check(policy, config, repository)
        reserve(assignment, config, 'github_read_file')
        return await client.github_file(policy, config, repository, path, ref)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_read_records(repository: str, kind: str = 'issues', number: int = 0) -> list[dict]:
        """Read up to ten issues, PRs, commits or workflow summaries; no logs or writes."""
        assignment, config = scope('github_read_records')
        client.repo_check(policy, config, repository)
        reserve(assignment, config, 'github_read_records')
        return await client.github_records(policy, config, repository, kind, number)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_read_tree(repository: str, ref: str) -> dict:
        """Read up to 200 immediate tree entries at an explicit ref."""
        assignment, config = scope('github_read_tree')
        client.repo_check(policy, config, repository)
        reserve(assignment, config, 'github_read_tree')
        return await client.github_tree(policy, config, repository, ref)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_search_code(repository: str, query: str) -> list[dict]:
        """Search plain code terms in exactly one approved repo; no query qualifiers."""
        assignment, config = scope('github_search_code')
        client.repo_check(policy, config, repository)
        reserve(assignment, config, 'github_search_code')
        return await client.github_search(policy, config, repository, query)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_read_pr_files(repository: str, number: int) -> list[dict]:
        """Read bounded PR file patches; at most 20 files, with truncated patches."""
        assignment, config = scope('github_read_pr_files')
        client.repo_check(policy, config, repository)
        reserve(assignment, config, 'github_read_pr_files')
        return await client.github_pr_files(policy, config, repository, number)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_repo_status(repository: str) -> dict:
        """Read bounded repo status for an approved repository."""
        assignment, config = scope("github_repo_status")
        client.repo_check(policy, config, repository)
        reserve(assignment, config, "github_repo_status")
        return await client.github_repo_status(policy, config, repository)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_recent_commits(repository: str, limit: int = 10) -> list[dict]:
        """Read bounded recent commits for an approved repository."""
        assignment, config = scope("github_recent_commits")
        client.repo_check(policy, config, repository)
        reserve(assignment, config, "github_recent_commits")
        return await client.github_recent_commits(policy, config, repository, limit)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_ci_status(repository: str, ref: str = "") -> dict:
        """Read bounded ci status for an approved repository."""
        assignment, config = scope("github_ci_status")
        client.repo_check(policy, config, repository)
        reserve(assignment, config, "github_ci_status")
        return await client.github_ci_status(policy, config, repository, ref or None)

    @mcp.tool()
    @observe("github", current_assignment)
    async def github_dependabot_alerts(repository: str, state: str = "open") -> list[dict]:
        """Read up to five Dependabot alerts for an approved repository; not a complete inventory."""
        assignment, config = scope("github_dependabot_alerts")
        client.repo_check(policy, config, repository)
        reserve(assignment, config, "github_dependabot_alerts")
        return await client.github_dependabot_alerts(policy, config, repository, state)
