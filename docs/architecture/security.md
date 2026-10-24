# Security and trust boundaries

Horology is designed for one person or a small trusted group, but it still separates human-readable records, agent permissions and secrets.

## Controls in place

- **No secrets in skills or Sheets.** Provider keys and OAuth client secrets are supplied through Secret Manager in cloud deployments or ignored private environment files locally.
- **Fixed MCP tools.** Agents receive named operations with validated, bounded inputs. The gateway does not expose arbitrary SQL, arbitrary provider endpoints or credentials.
- **Least-privilege database roles.** The gateway, document graph, sync job and migrations use different Neon credentials. Runtime roles cannot perform owner-level migrations.
- **Workspace-scoped graph access.** Google sign-in is matched to an allowed user, service grant and workspace. OAuth tokens are stored hashed.
- **Fail-closed spending controls.** Tavily and Firecrawl reservations use shared database-backed daily and monthly budgets. Database or pricing uncertainty blocks the call.
- **Network and output bounds.** Public-URL tools reject local, private, link-local and metadata addresses, disable redirects and environment proxies where applicable, and bound returned content.
- **Safe operations data.** Structured logs exclude credentials, document bodies and raw exception messages; client errors carry a category and request ID.
- **Private local services.** Local document-graph and gateway ports bind to `127.0.0.1`. The shared Docker network is for container-to-container access, not internet exposure.
- **Protected publishing.** Cloudflare Pages publishing checks the signed-in email, registered workspace project and exact-email Access policies before uploading.
- **Release checks.** CI, dependency audits, migrations and operator smoke checks are documented and repeatable.

## Boundaries that remain

- Horology is not a general multi-tenant product. Workspace creation, account grants, connector setup and Cloudflare provisioning still need an operator.
- A small group is expected to share trust in the same Sheets and Drive folders. Google permissions remain the primary control for those files.
- Native Google Drive, GitHub or other platform connectors are outside the gateway's policy and budget enforcement. Their scopes must be reviewed in the platform that provides them.
- Local document-graph mode has no application authentication. Its localhost-only binding is therefore a required boundary.
- Gateway provider budgets are shared across clients, not allocated per workspace or person.
- Sheet-to-Neon synchronization is eventual. The live Sheet may contain a change that the graph has not copied yet.
- A single verified email should resolve to one active workspace for sensitive write operations. Some of this is an operating rule as well as an enforced database constraint.
- Subscription-agent behavior also depends on the installed skill version and the host platform's permission model. A skill is guidance, not a sandbox.

## Operator checklist

1. Keep private files out of Git and build contexts. Watchmaker's live `runtime/hermes-data/` is ignored in its own repository.
2. Grant only the required Google account, workspace and MCP service access.
3. Use the dedicated runtime database roles; run Alembic with the owner connection only.
4. Keep local MCP ports on loopback and Cloud Run services behind their configured OAuth flow.
5. Review native connector scopes separately from gateway permissions.
6. Verify the deployed policy and harmless status tools after each release.
7. Revoke access and rotate credentials when a person or machine leaves the trusted group.

Implementation detail lives in [MCP services](mcp/mcp-services.md), [gateway](mcp/gateway.md), [document graph](mcp/document-graph.md), [data model](data/data-model.md) and the [access runbook](../runbook/mcp/access.md).
