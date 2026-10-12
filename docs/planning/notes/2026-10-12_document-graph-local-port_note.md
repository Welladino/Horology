# Local document-graph port for host MCP clients

Date: 2026-10-12

Published `127.0.0.1:8765:8765` in the independent document-graph Compose project. Laptop clients use `http://127.0.0.1:8765/mcp`; Hermes retains `http://document-graph-mcp:8765/mcp` on the shared Docker network. Local document-graph has no application OAuth and includes write/embedding tools. Cloud Run IAM configuration was not changed.

Verified: 78 tests passed, including an exact localhost-only Docker port binding and host/internal HTTP reachability. A host MCP client initialized and discovered all seven tools without invoking any tool or paid provider. Hermes was restored to its prior stopped state and the disposable test database removed. No Codex connection configuration, commit or push was performed.
