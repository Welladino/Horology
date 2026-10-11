# Root shared runtime

Moved mcp-servers/runtime to root shared-runtime, renamed package/distribution to horology_runtime / horology-shared-runtime, and split logging configuration, safe error classification, timeout settings and operation wrappers into separate modules. Both MCP services import the same package. HTTP/Postgres exception classifiers are optional so future Hermes extensions can reuse the package without installing MCP or DB dependencies. Hermes upstream itself was not patched or instrumented.

Docker contexts now use the repository root, with root .dockerignore explicitly allowing only runtime and approved service source/dependencies/public CA. Each image copies only its own service and the common package. Removed the obsolete mcp-servers .dockerignore. Updated native editable install commands and current docs. Historical notes retain their original paths.

Validation: 48 full repository/gateway tests passed; both images rebuilt and restarted; authenticated gateway smoke and document graph seven-tool discovery passed. Both containers imported all four root-package modules and private environment files were absent from packaged application/runtime paths. A Python -S check proved imports without optional MCP/HTTP/Postgres libraries. No paid provider calls, DB writes or quota resets needed.
