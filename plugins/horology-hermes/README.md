# Horology skills for Hermes

This package contains skills used only by the Hermes deployment. They are not
part of the Claude or Codex subscription-agent distributions.

- `horology-coordinator` gives Hermes' protected `default` profile its
  planning, routing, approval and review logic.

Shared workflow, specialist and MCP skills remain in the other
`plugins/horology-*` packages. The Hermes bootstrap installs those shared
skills for Coordinator and Operator, removes the subscription-agent supervisor
from both profiles, and installs `horology-coordinator` only for Coordinator.
