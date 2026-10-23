# Running Tests and Security Audits

## Test suite

Tests are grouped first by what they need, then by the repository component:

| Folder | Needs | Behavior |
| --- | --- | --- |
| `tests/unit/` | Nothing external | Fast tests with fakes and mocks |
| `tests/integration/` | Disposable PostgreSQL or a local HTTP server started by the test | Database tests skip when their explicit test URLs are absent |
| `tests/system/` | The real Docker Compose stack and populated private environment | Skips when Docker is unavailable |
| `tests/manual/` | An operator-prepared local service | Smoke helpers, not collected by pytest |
| `tests/support/` | — | Shared helpers; contains no tests |

Inside each kind, folders mirror components such as `document_graph_core/`, `jobs/`, `mcp_servers/` and `shared_runtime/`. Any test that touches a real database belongs in integration, even when most of the surrounding feature can be unit-tested. Keep test filenames unique across the entire tree. Property-based failures should also gain a plain regression example.

Install the shared packages into the development environment first:

```bash
.venv/bin/python -m pip install --no-deps -e shared-runtime -e document-graph-core
```

### Unit tests: no database, network or Docker

```bash
.venv/bin/python -m pytest tests/unit -q
```

### Integration tests: a disposable migrated Postgres

Start a throwaway pgvector database, migrate it, and point the tests at its logins. The passwords are test-only values for this throwaway container:

```bash
docker run -d --name horology-test-pg -e POSTGRES_PASSWORD=ci-admin-only -p 127.0.0.1:55432:5432 pgvector/pgvector:0.8.0-pg16
```

```bash
DATABASE_URL=postgresql+psycopg://postgres:ci-admin-only@127.0.0.1:55432/postgres .venv/bin/python -m alembic upgrade head
```

```bash
GATEWAY_TEST_DATABASE_URL=postgresql://postgres:ci-admin-only@127.0.0.1:55432/postgres GATEWAY_TEST_RUNTIME_URL=postgresql://horology_gateway:ci-runtime-only@127.0.0.1:55432/postgres GRAPH_TEST_RUNTIME_URL=postgresql://horology_graph:ci-graph-only@127.0.0.1:55432/postgres .venv/bin/python -m pytest tests/integration -q
```

Without those variables, integration tests are skipped, not failed.

### System tests: the real Docker Compose stack

```bash
.venv/bin/python -m pytest tests/system -q
```

They need Docker running and `.env` populated, and are skipped when Docker isn't up. They build and start the stack and leave it running.

### Everything

```bash
.venv/bin/python -m pytest tests/ -q
```

### Gateway HTTP smoke check (by hand)

```bash
.venv/bin/python tests/manual/gateway/smoke.py
```

It needs a disposable migrated `GATEWAY_DATABASE_URL` and makes no provider calls. Its private test clients are in `tests/manual/gateway/fixtures/private/`, which Git ignores.

## Security checks: one local report

```bash
scripts/security/run_checks.sh
```

It writes `reports/security/summary.md`, replaced on every run, with each tool's raw output in `reports/security/raw/` (`reports/` is ignored by Git). It exits 1 if anything would fail Cloud Build. Add `--skip-images` to leave out the two image builds and scans (about 20 seconds instead of a few minutes).

| Check | Tool | Fails on | Also in Cloud Build |
|---|---|---|---|
| Python dependency vulnerabilities (dev venv and each `requirements.txt`) | pip-audit | any known vulnerability | yes (`scripts/ci/check.sh`) |
| Python security lint | Bandit (`.bandit.yaml`) | any finding not marked `# nosec <check>: <reason>` | yes |
| Secrets and misconfigurations in the source | Trivy `fs` | HIGH/CRITICAL | yes |
| Image vulnerabilities and secrets | Trivy `image` | fixable HIGH/CRITICAL | yes |
| Image licences | Trivy `image --scanners license` | forbidden (CRITICAL, e.g. AGPL, SSPL) | yes |
| Secrets in the Git history | gitleaks (values redacted) | any finding | no (Cloud Build receives no `.git`) |

**What the source scan sees:** only the files Git tracks or would track, as Cloud Build does. Local secrets (`.env`, `.auth/`, the private test clients) are never read.

**Tool versions:** Trivy and gitleaks run from pinned Docker images (`aquasec/trivy:0.75.0`, `zricethezav/gitleaks:v8.30.1`); keep Trivy in step with `cloudbuild.yaml`. Bandit and pip-audit come from the dev venv.

**A new Bandit finding:** fix it. If it's intended (for example, SQL whose text is fixed in code), mark that line `# nosec <check>: <reason>`. Put the marker on a line of the statement outside any string, such as after the closing `"""`, never inside the SQL.

**If gitleaks finds a secret:** treat it as exposed. Rotate it first, then remove it from the history.

## GitHub Actions

`.github/workflows/ci.yml` runs on every push and pull request (and by hand from the Actions tab). It runs the same gates as Cloud Build in three parallel jobs:

- **Tests, Bandit and pip-audit:** `scripts/ci/check.sh` against a Postgres service container. All migrations run from empty, and an unexpected skip fails the job.
- **Source:** Trivy secrets and misconfigurations, plus gitleaks over the **whole Git history**, which Cloud Build can't scan.
- **Images:** for each of the two images, a build, the image contract check, then Trivy for vulnerabilities, secrets and licences.

The system (Docker stack) tests skip there: they need the stack's `.env` files. Nothing in the workflow deploys or uses a production credential; the token is read-only, scanners run as pinned Docker images, and GitHub's own actions are pinned to commits.

The free plan has no branch protection for private organisation repositories, so a failing run marks the commit red and sends an email, but it doesn't block the push. Check the Actions tab before deploying.

## Test coverage: a separate report

```bash
scripts/testing/coverage.sh
```

It writes `reports/coverage/summary.md` (the files below 100%, with missing lines) and `reports/coverage/html/index.html` (line by line), replaced on every run. Set the three test-database variables (above) to include integration tests; otherwise it measures unit tests only. It's a view, not a gate: there's no minimum percentage.

## Dependency security audit (`pip-audit`), one tool at a time

```bash
source .venv/bin/activate

# Local dev venv (Alembic, pytest, and the mirrored MCP server deps)
pip-audit

# Each MCP server's actual production requirements.txt (what its Dockerfile installs)
pip-audit -r mcp-servers/document-graph/requirements.txt
pip-audit -r mcp-servers/mcp-gateway/requirements.txt
```

Run all three whenever a dependency is added or bumped, and periodically (e.g. before any deployment) since a package can gain a new CVE after it's already pinned. If a vulnerability is found: check what it actually is (`pip-audit --desc`) before reflexively bumping — some are low-relevance to this project's actual usage (e.g. a local-multi-user issue on a single-user dev machine), but bumping to the fixed version is still usually the right call when there's no compatibility cost (re-run the test suite after bumping to confirm nothing broke).

Note: `pip-audit` only checks Python dependencies here — Hermes's own bundled dependency vulnerabilities (found via `hermes doctor` / `hermes security audit` inside the container, not this tool) are tracked separately, see [`docs/planning/notes/2026-08-05_hermes-hardening_note.md`](https://github.com/Welladino/Horology/blob/main/docs/planning/notes/2026-08-05_hermes-hardening_note.md).

Docker images install the shared runtime and `document-graph-core` from the shared build context automatically.
