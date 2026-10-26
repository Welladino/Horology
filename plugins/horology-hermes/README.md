# Horology skills for Hermes

This package contains skills used only by the Hermes deployment. They are not
part of the Claude or Codex subscription-agent distributions.

- `horology-coordinator` gives Hermes' protected `default` profile its
  planning, routing, approval and review logic.
- `horology-composio-reader` gives Coordinator bounded, read-only access to
  live Pipeline, Locations, registers, Drive metadata and linked Docs.
- `horology-composio-guide` gives Operator the maintained Composio MCP
  discovery, Google Workspace routing, approval and verification procedure.

Shared workflow, specialist and MCP skills remain in the other
`plugins/horology-*` packages. The Hermes bootstrap installs those shared
skills for Coordinator and Operator, removes the subscription-agent supervisor
from both profiles, installs `horology-coordinator` only for Coordinator, and
installs `horology-composio-reader` only for Coordinator and
`horology-composio-guide` only for Operator.
