# Running Tests and Security Audits

## Test suite

Two tiers, in `tests/`:

### Unit tests (`tests/mcp_servers/`) — mocked, no Docker required

```bash
source .venv/bin/activate
python3 -m pytest tests/mcp_servers/ -v
```

**What's covered:** input validation (`doc_type` checks, limit clamping), response shaping (which fields get extracted from a raw API response), content truncation (the 40,000-char caps on `get_pull_request_diff`/`get_file_content`), repo-scoping (every GitHub call stays scoped to `GITHUB_REPO`, including a test that a query trying to inject a different `repo:` filter can't escape the configured repo), and a regression test for the real embedding-dimension bug (`_embed` must always send `dimensions: 768` — if that parameter is ever dropped, embeddings silently come back at 3072 dims again, which breaks the `document_embeddings` schema).

**What's NOT covered, deliberately:** real integration with Neon, OpenRouter, or the GitHub API. Both real bugs found during this project (the embedding dimension mismatch, pgvector's HNSW dimension limit) were caught by testing live against the real API, not by unit tests — mocks wouldn't have caught either, since they encode assumptions about the response shape rather than discovering the real one. Verifying a new integration point hands-on (a real API call, checked directly) remains the standing practice for anything touching a system outside this repo's own logic — this suite protects against regressions in *our* code, not against the external world changing.

#### Adding a test for a new tool

Follow the existing pattern in `tests/mcp_servers/test_document_graph.py` / `test_github_monitor.py`: import `server.py` fresh via `importlib` (so each test file gets an isolated module, not a shared one polluted by another file's fake env vars), mock `_connect()`/`_get()`/`httpx.post` at the boundary, assert on what the function actually did (query params sent, response shape returned), not on internal implementation details.

### Container/isolation tests (`tests/test_docker_stack.py`) — real Docker, no mocks

```bash
source .venv/bin/activate
python3 -m pytest tests/test_docker_stack.py -v
```

Drives the real `docker compose` CLI: builds and starts the actual stack, then asserts on the isolation properties that were previously only checked by hand throughout this project — every container reaches a running state, none run `--privileged`, Hermes has exactly one host mount (scoped to `hermes-data/`), neither MCP server has any host mount, neither MCP server is reachable from the host, both ARE reachable from inside the `hermes` container (the internal network works), and the dashboard rejects unauthenticated requests. Automates the `docker inspect`/`curl` checks this project ran manually after every `docker-compose.yml` change.

**Requires:** Docker running, and `.env` populated with real credentials (build/startup needs them). Automatically skipped (not failed) if Docker isn't available, so `pytest tests/` still runs cleanly on a machine without Docker running. Leaves the stack running afterward — doesn't tear down, since these containers are meant to stay up.

**What's NOT covered:** real tool behavior through the containers (e.g. that `write_document` called through the real running stack actually writes to Neon). That's a further "real end-to-end integration test" tier — not yet built, would need its own test-scoped credentials.

### Running everything

```bash
python3 -m pytest tests/ -v   # runs both tiers; Docker tier auto-skips if Docker isn't up
```

## Dependency security audit (`pip-audit`)

```bash
source .venv/bin/activate

# Local dev venv (Alembic, pytest, and the mirrored MCP server deps)
pip-audit

# Each MCP server's actual production requirements.txt (what its Dockerfile installs)
pip-audit -r mcp-servers/document-graph/requirements.txt
pip-audit -r mcp-servers/mcp-gateway/requirements.txt
```

Run all three whenever a dependency is added or bumped, and periodically (e.g. before any deployment) since a package can gain a new CVE after it's already pinned. If a vulnerability is found: check what it actually is (`pip-audit --desc`) before reflexively bumping — some are low-relevance to this project's actual usage (e.g. a local-multi-user issue on a single-user dev machine), but bumping to the fixed version is still usually the right call when there's no compatibility cost (re-run the test suite after bumping to confirm nothing broke).

Note: `pip-audit` only checks Python dependencies here — Hermes's own bundled dependency vulnerabilities (found via `hermes doctor` / `hermes security audit` inside the container, not this tool) are tracked separately, see [`docs/planning/notes/2026-08-06_hardening-config-audit_note.md`](../../planning/notes/2026-08-06_hardening-config-audit_note.md).

For both MCP servers, install the shared runtime into the native development environment before tests: `.venv/bin/python -m pip install --no-deps -e shared-runtime`. Docker images install it from the shared build context automatically.

Gateway tests and the local HTTP smoke helper live in `tests/mcp_servers/gateway/`. Run the helper with `.venv/bin/python tests/mcp_servers/gateway/smoke.py` and a disposable migrated `GATEWAY_DATABASE_URL`. The helper does not call external providers.
