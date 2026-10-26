# Operational scripts

These scripts configure or verify running systems. They are grouped by the
system they operate:

- `hermes/` — local Hermes deployment and profile bootstrap.
- `mcp/` — MCP access administration, protected Pages registration and live
  deployment checks.
- `claude/` — Claude skill packaging.
- `codex/` — Codex plugin packaging.

Security scanners and repository audit checks belong in `scripts/security/`.
The MCP administration scripts remain here because they can change live access
or deployment configuration; the live check remains here because it verifies
deployed services rather than scanning source code.
