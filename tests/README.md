# Tests

Organised first by **kind** (what a test needs to run), then by the part of the repo it covers.

| Folder | Kind | Needs | When it runs |
|---|---|---|---|
| `unit/` | Unit: one piece of our code, with fakes and mocks for the database, network and providers | Nothing | Always; fast (about a second) |
| `integration/` | Integration: our code against a real, disposable, migrated Postgres, through the same restricted logins the services use | `GRAPH_TEST_RUNTIME_URL`, `GATEWAY_TEST_DATABASE_URL`, `GATEWAY_TEST_RUNTIME_URL` | Skipped, not failed, when they aren't set |
| `system/` | System: the real Docker Compose stack (containers, mounts, networks, dashboard sign-in) | Docker running, `.env` populated | Skipped when Docker isn't up |
| `manual/` | Helpers run by hand, not collected by pytest: the gateway's HTTP smoke check and its private test clients (`gateway/fixtures/private/`, ignored by Git) | A local gateway | On demand |
| `support/` | Helpers shared by tests of different kinds (repository paths, sheet rows, entity fakes, gateway and OAuth fakes); no tests | | |

Inside each kind, folders follow the repo:

- `document_graph_core/`: the shared graph package (`document-graph-core/`). It isn't called `graph_core/`, which would shadow the package on import.
- `jobs/`: the sync job.
- `mcp_servers/gateway/`, `mcp_servers/document_graph/`: the two MCP servers.
- `shared_runtime/`: the shared runtime (`horology_runtime`).

Rules:

- **Placing a test.** A test that touches a real database goes in `integration/`, even if most of its file is unit tests: split the file, and put any helpers both halves need in `support/`.
- **File names.** Test file names are unique across the whole tree, since pytest imports them by name.
- **Not covered here.** Live provider calls (OpenRouter, Tavily, Google) and the deployed services: checked by hand, or with `scripts/ops/live_check.py` after a deploy.

Commands: [running tests and audits](../docs/runbook/testing/running_tests_and_audits.md).
