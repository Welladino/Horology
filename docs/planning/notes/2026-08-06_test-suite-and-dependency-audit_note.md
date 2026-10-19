# Test suite, container checks and dependency audits

## Topic
- test-suite-and-dependency-audit

## Context

Until 2026-08-06 every check was manual: does `write_document` reject a bad `doc_type`, does GitHub search stay inside its repository, can the host reach an MCP container, are containers isolated from the host filesystem. Three items were raised together: turn those checks into tests, audit dependencies, and confirm containers can't reach the host's real filesystem.

## Decisions

**Unit tests, mocked.** A pytest suite was added that needs no Docker, database or API to run: input validation, response shaping, truncation, repository scoping (including an attempt to inject a different `repo:` filter), and a named regression test for the embedding-dimension bug (`_embed` must request `dimensions: 768`, or embeddings silently become 3,072-dimensional and break the schema). It deliberately does not claim integration coverage; both real bugs found so far were caught by live testing.

**Container checks, separate and skippable.** A second module drives the real `docker compose` CLI through `subprocess` (no Docker SDK dependency). It checks that every container runs, none is privileged, Hermes has exactly one host mount and the MCP containers none, the MCP servers are unreachable from the host but reachable from inside Hermes (a 400, 404 or 406 is the expected answer), and the dashboard refuses an unauthenticated request. It skips itself when Docker or `.env` is missing, so `pytest tests/` stays fast anywhere. It doesn't tear the stack down, because the founder works against the running containers.

**pip-audit on every dependency set.** Run against the dev environment and each MCP server's `requirements.txt`. The one finding, `pytest==8.3.4` (`PYSEC-2026-1845`, a local multi-user `/tmp` issue), was fixed by moving to 9.0.3 and re-running both the tests and the audit. `pip-audit` became a standing dev tool.

**Host filesystem.** Confirmed with `docker inspect` rather than changed: only Hermes has a mount, scoped to `hermes-data/`, and nothing is privileged. Running as root inside a container was a separate, lower-priority concern.

## Rationale

A suite that runs in seconds with no setup is far more likely to be run before a change ships than one needing the whole stack. Automating the container checks turns "remember to re-check by hand after every Compose change" into one command. `pip-audit` costs minutes and found a real issue.

## Impact

- The tests have since been reorganised into `tests/unit/`, `tests/integration/` (disposable PostgreSQL) and `tests/system/` (the Docker stack), and both MCP images now run as a non-root user (UID 10001). Where a new test goes: [`tests/README.md`](../../../tests/README.md). How to run tests and audits: [runbook](../../runbook/testing/running_tests_and_audits.md).
- The same tests and audits now gate every release in Cloud Build and GitHub Actions ([Cloud](../../architecture/cloud/cloud-infrastructure.md#release)).

## Follow-Ups

- An end-to-end tier that calls tools through the live stack against real services would need test-scoped credentials and clean-up, so production data isn't polluted.
- Re-run `pip-audit` whenever dependencies change; a clean result today says nothing about next month.
