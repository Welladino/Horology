# GitHub monitoring through the restricted gateway

The standalone github-monitor server is retired. Second-Soul and Code Sentinel use mcp-gateway with separate GitHub-only authenticated assignments. Repository scope comes from policy and assignment intersection; current approved repos are Welladino/Horology and Welladino/Article_aggregator_agent.

Read gateway_status before work. Monitoring tools: github_repo_status, github_recent_commits, github_ci_status, github_dependabot_alerts; other reads: github_read_records, github_read_file, github_read_tree, github_search_code, github_read_pr_files. Dependabot returns at most five alerts; PR patches are bounded and incomplete. Report limitations honestly.

GitHub token resides in gateway .env.local with read-only Contents, Metadata, Issues, Pull requests, Actions and Dependabot alerts. GITHUB_REPO is not a gateway input. Local Hermes profiles hold only their own gateway bearer credential, with a structured tools.include filter. Authenticated server assignment enforcement remains authoritative.

Start the main stack, then gateway with compose.yaml and compose.hermes-network.yaml as described in ../docker/running_all_services.md. Use Hermes MCP CLI/configuration writer to change profile connections; never edit live config.yaml directly. Persona sources live under personas/ and must be synced. Local assignments expire in 24 hours with persistent two-call limits; provisioning for recurring runs remains pending.
