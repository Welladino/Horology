# Implementation Note

## Topic
- test-suite-and-dependency-audit

## Context

Three hardening items raised together: (a) formalize the manual verification done all session into an actual test suite, (b) run a dependency security audit (`pip-audit`), (c) check whether containers can reach the host's real root filesystem.

## Decision

**(a) Test suite: `tests/mcp_servers/`, pytest, mocked (no Docker/DB/API calls required to run).** Covers `document-graph-mcp` and `github-monitor-mcp` — our own code, most directly testable in isolation. 19 tests: input validation, response shaping, content truncation, GitHub repo-scoping (including a test that a query trying to inject a different `repo:` filter can't escape the configured repo), and a named regression test for the real embedding-dimension bug found earlier this session (`_embed` must always request `dimensions: 768`, or embeddings silently revert to 3072 dims and break the schema). Deliberately does not cover real integration with Neon/OpenRouter/GitHub — both real bugs found this project were caught by live testing, not by unit tests, and the suite's own docs say so explicitly rather than implying broader coverage than it has.

**(b) `pip-audit` — run against all three Python dependency sets** (the shared dev venv, and each MCP server's own production `requirements.txt`). Found one real vulnerability: `pytest==8.3.4` (`PYSEC-2026-1845`, a local-multi-user `/tmp` directory privilege issue on UNIX, low relevance on a single-user dev machine but cheap to fix) — bumped to `9.0.3`, re-ran the full test suite to confirm no breaking changes, re-ran `pip-audit` to confirm clean. Both MCP servers' own `requirements.txt` were already clean.

**(c) Investigated, no fix needed.** The founder's actual concern was whether containers can reach the *host's* real root filesystem (not whether the process runs as UID 0 inside its own container — a related but different, lower-priority question). Confirmed via `docker inspect`: both MCP servers have zero mounts at all (completely sealed, no host path reachable whatsoever); Hermes has exactly one mount, scoped to `Horology/hermes-data/` (cannot see the founder's home directory or `Article_aggregator_agent`). None are `--privileged`. This was already true from the original `docker-compose.yml` design — confirmed, not changed. Running as root *inside* the container (all three currently do) was explicitly deprioritized as a separate, lower-severity item given the mount isolation already holds — see Follow-Ups.

## Rationale

The test suite formalizes exactly the kind of check that's been done by hand all session (does `write_document` reject a bad `doc_type`, does the GitHub search stay scoped, does the embedding request send the right dimension) without requiring Docker or real credentials to run, which matters given this project's actual workflow is mostly manual `docker exec`/`hermes chat -q` verification — a fast, no-setup-required suite is more likely to actually get run before a change ships than one requiring the full stack up. `pip-audit` is a five-minute, zero-cost check with a real (if minor) finding — worth running periodically, not just once.

## Impact

- `tests/mcp_servers/test_document_graph.py` and `test_github_monitor.py` — 19 passing tests, runnable via `python3 -m pytest tests/ -v`.
- `requirements-dev.txt` updated: `pytest` bumped to the patched version, `pip-audit` added as a standing dev tool.
- `docs/runbook/testing/running_tests_and_audits.md` — how to run both, and the explicit scope boundary (unit-level, not integration) so future use of this suite doesn't get mistaken for broader coverage than it has.

## Follow-Ups

- Containers running as root inside their own container (not the host-root question, already resolved) — worth fixing eventually via a non-root `USER` in the two Dockerfiles we own (`document-graph`, `github-monitor`); leaving Hermes's own vendored image as-is, since patching a third-party image would mean fighting how Nous Research built it (their `PUID`/`PGID` env vars suggest a specific internal mechanism already, worth understanding before assuming it needs a fix). Not urgent given the mount isolation already holds.
- Re-run `pip-audit` periodically (a natural moment: before any future deployment, or whenever a dependency is bumped) — a clean result today doesn't mean clean next month.
- If the test suite ever needs coverage of the two other repo pieces (Alembic migrations, persona-sync correctness), scope that as its own addition rather than assuming this suite implicitly covers them.
