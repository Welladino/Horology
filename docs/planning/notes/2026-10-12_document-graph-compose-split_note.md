# Independent document-graph Compose project

Date: 2026-10-12

Document-graph now runs in `horology-document-graph-mcp`, with its own `mcp-servers/document-graph/compose.yaml`. The root `horology` project runs only Hermes. The optional document-graph `compose.hermes-network.yaml` joins `horology_default` as `document-graph-mcp`; use both files when Hermes connectivity is needed. No host port is published, and documents remain in Neon. Cloud Run was not changed.

Updated the local service runbook, document-graph README, architecture overview and full-stack fixture. The fixture starts both projects and waits for their HTTP readiness, avoiding the initial new-container startup race.

Verification: 78 tests passed using disposable PostgreSQL; Docker Desktop lists three independent projects. A bounded invalid JSON-RPC POST from Hermes reaches document-graph and returns the expected 400. The disposable PostgreSQL container was removed afterward. No commit or push.
