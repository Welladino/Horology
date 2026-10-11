# Document graph MCP

Separate Neon document graph and OpenRouter embeddings service.

- `server.py`: MCP entrypoint.
- `document_graph/tools.py`: registers the seven fixed document tools.
- `document_graph/integrations/neon/client.py`: parameterized document persistence and graph orchestration.
- `document_graph/integrations/openrouter/client.py`: embedding requests; no database access.
- `requirements.txt`: service-specific pinned dependencies.

Copy `.env.example` to `.env` for a new setup. Required: DATABASE_URL_POOLED (Neon pooled connection) and OPENROUTER_API_KEY (embeddings). Optional: EMBED_MODEL, default google/gemini-embedding-001, and DOCUMENT_GRAPH_BIND, default 0.0.0.0. Embeddings remain 768-dimensional to match the database. DATABASE_URL is not an environment input; no duplicate connection string is needed. Root Compose loads the service-specific .env; Python does not load it itself. Keep .env excluded from Git and images. Root credentials still required by other components should remain there.

0.0.0.0 binds the container listener to its network interfaces, not to a chosen remote server. Compose does not publish this service's port to the host. Hermes reaches it by Docker service name, http://document-graph-mcp:8765/mcp. Binding to 127.0.0.1 inside the container would prevent other containers connecting. No application authentication is implemented here; do not expose this service publicly before adding cloud authentication and embedding limits.

Application operation logs emit JSON to stdout with tool, integration, duration, outcome and correlation ID. Tool errors expose only a category and request ID; arguments, documents, credentials and raw exception messages are excluded. Neon has a five-second connection timeout, ten-second statement timeout and three-second lock timeout. OpenRouter retains its thirty-second HTTP timeout. No automatic retries. Inspect locally with `docker compose logs document-graph-mcp`.

Timeout settings and logging/error handling are imported from the common package at `../../shared-runtime/horology_runtime/`. Change `settings.py` or `operations.py` there and rebuild both images. Native development requires installing the shared runtime as described in its README. Docker build context is the repository root, using its secret-safe `.dockerignore`; use the documented Compose commands.
