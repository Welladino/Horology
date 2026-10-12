# Architecture

Standing, current-state reference docs for Horology's design — updated in place as the system evolves, not dated/versioned like `docs/planning/`.

- [`system_overview.md`](system_overview.md) — runtime architecture (the three containers), dispatch mechanism, document graph, personas, current subagent roster.

- [`subscription_agents.md`](subscription_agents.md) — Drive/Sheets-driven subscription-agent workflow, skills, review stages and ClickUp integration.

- [MCP cloud operations](../runbook/architecture/mcp_operations.md) — source-to-release diagrams, service identities, security gates, storage and external-client OAuth.

- [GCP access policy](../runbook/architecture/gcp_access.md) — daily viewing, deployer impersonation, protected administration, local gcloud profiles and scoped IAM grants.
