# Operational scripts

These scripts configure or verify running systems. They are grouped by the
system they operate:

- `hermes/` — local Hermes deployment and profile bootstrap.
- `mcp/` — MCP access administration, protected Pages registration and live
  deployment checks.
- `gcp/` — one-command Cloud Run release of the MCP services
  (`docs/runbook/gcp/mcp_deployment.md`).
- `claude/` — Claude skill packaging and the Claude supervisor's dispatch adapter.
- `codex/` — Codex plugin packaging: each plugin's Codex config in `codex/plugins/<plugin>/` and
  the Codex supervisor's dispatch adapter.

Security scanners and repository audit checks belong in `scripts/security/`.
The MCP administration scripts remain here because they can change live access
or deployment configuration; the live check remains here because it verifies
deployed services rather than scanning source code.
