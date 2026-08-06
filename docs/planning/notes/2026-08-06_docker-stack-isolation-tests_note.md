# Implementation Note

## Topic
- docker-stack-isolation-tests

## Context

The existing unit test suite (`tests/mcp_servers/`, from the prior test-suite note) was deliberately mocked, with no Docker/DB/API dependency. Following up on whether to also test the actual Docker Compose stack — the container build/start/isolation properties that were, up to this point, only ever verified by hand (`docker inspect`, `curl` from host vs. from inside the `hermes` container) after every `docker-compose.yml` change throughout this project.

Scoped this into two tiers before building anything: (1) containers build/start cleanly and the isolation properties hold, (2) a further real end-to-end integration test (tools called through the real running stack, hitting real Neon/GitHub). Built (1) now; (2) deferred as a separate, later piece of work.

## Decision

**Added `tests/test_docker_stack.py`** — drives the real `docker compose` CLI via `subprocess` (no Docker Python SDK dependency added; this project has shelled out to the `docker`/`docker compose` CLI directly all session and it works reliably). 14 tests:

- All three containers reach `Running: true` after `docker compose up -d`.
- None run `--privileged`.
- Hermes has exactly one host mount (`hermes-data/` → `/opt/data`); both MCP servers have zero host mounts.
- Neither MCP server is reachable from the host (`httpx.ConnectError` expected on `localhost:8765`/`:8766`).
- Both MCP servers ARE reachable from inside the `hermes` container (`docker exec ... curl` — a 400/404/406 response, not a connection failure, is the expected/correct result, matching how we've verified this by hand all session).
- The dashboard rejects an unauthenticated bare request (302 or 401, never 200).

Kept in a separate file from `tests/mcp_servers/`, not merged into one `pytest tests/` command that silently requires Docker — this test module is auto-skipped (via `pytest.mark.skipif`) if Docker isn't running or `.env` doesn't exist, so `pytest tests/` still runs cleanly and fast on a machine without Docker up, while still being included when it's available.

**Does not tear down the stack after running** — deliberately. This project's containers are meant to stay running (the founder actively works against them); a test suite stopping them as a side effect of running would be a surprising, disruptive side effect for what's meant to be a verification step.

Verified: ran against the real, already-running stack — 14/14 passed. Ran combined with the existing unit suite (`pytest tests/ -v`) — 33/33 passed together, confirming the two tiers coexist without interference.

## Rationale

Every property this suite checks was previously a manual step repeated after each Docker-related change this session (verifying isolation after adding the GitHub monitor server, after switching document-graph-mcp's transport, etc.) — automating it converts "remember to re-check this by hand" into "run one command," which is the same value proposition as the unit test suite, just for a different layer (container/network config vs. application code). Kept as `subprocess` calls to the real CLI rather than a Docker SDK to avoid adding a dependency purely for something the existing manual workflow already does reliably.

## Impact

- `tests/test_docker_stack.py` — 14 tests, requires Docker + real `.env`, auto-skips otherwise.
- `docs/runbook/testing/running_tests_and_audits.md` restructured to describe both test tiers separately (unit vs. container), including what each does and doesn't cover, so the suite's actual scope stays clear as it grows.

## Follow-Ups

- Build the deferred second tier (real end-to-end: call tools through the live containers against real Neon/GitHub) as its own piece of work, likely needing dedicated test-scoped credentials (e.g. a disposable test row cleanup pattern for `write_document`, to avoid polluting the real document graph with test data) rather than reusing production credentials directly.
- If `docker-compose.yml` ever adds a fourth service, extend the `@pytest.mark.parametrize` lists in this file rather than duplicating test bodies.
