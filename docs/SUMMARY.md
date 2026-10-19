# Summary

## Start here

* [How Horology works](runbook/setup/how-horology-works.md)
* [Set up Horology](runbook/setup/setup.md)
* [Horology skills and how to use them](runbook/setup/skills.md "Skills")

## Architecture

* [Architecture](architecture/overview.md "Overview")
* [Subscription agents](architecture/subscription-agents/subscription-agents.md)
  * [Apps Script projects](architecture/subscription-agents/apps-script.md)
* [MCP services](architecture/mcp/mcp-services.md)
  * [Gateway](architecture/mcp/gateway.md)
  * [Document graph](architecture/mcp/document-graph.md)
* [Data model](architecture/data/data-model.md)
* [Cloud infrastructure](architecture/cloud/cloud-infrastructure.md)
* [Hermes agents](architecture/hermes/hermes-agents.md)

## Runbook

* [Subscription-agent runbooks](runbook/subscription-agents/README.md "Subscription agents")
  * [Subscription-agent operations](runbook/subscription-agents/operations.md "Operations")
  * [Claude skills and connectors](runbook/subscription-agents/claude_skills.md)
  * [Horology Codex setup](runbook/subscription-agents/codex_setup.md "Codex setup")
  * [Horology plugin maintenance](runbook/subscription-agents/horology_plugin.md "Plugin maintenance")
  * [Apps Script projects: setup and publishing](runbook/subscription-agents/clasp.md "Apps Script projects")
* [MCP Servers](runbook/mcp/README.md "MCP servers")
  * [Users, workspaces and MCP access](runbook/mcp/access.md)
  * [Document graph MCP server (local)](runbook/mcp/document_graph_server.md "Document graph server (local)")
* [Deploy the MCP services to Cloud Run](runbook/gcp/mcp_deployment.md "Cloud Run deployment")
  * [MCP release builds](runbook/gcp/cloud_build.md)
  * [Monitoring: dashboard and logs](runbook/gcp/monitoring.md "Monitoring")
  * [Operator access and checks](runbook/gcp/operator_checks.md)
* [Alembic / Neon Workflow](runbook/db/alembic_workflow.md "Database migrations")
* [Running Horology services](runbook/docker/running_all_services.md "Running services locally")
  * [Hermes Setup](runbook/docker/hermes_setup.md "Hermes setup")
* [Running Tests and Security Audits](runbook/testing/running_tests_and_audits.md "Tests and audits")
