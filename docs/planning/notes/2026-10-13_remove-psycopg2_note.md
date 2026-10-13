# Implementation Note

## Topic
- remove-psycopg2

## Context
- After document-graph moved to Psycopg 3, `psycopg2` was still used by the gateway's Supabase metadata adapter (the only runtime use), by Alembic and two role-creating migrations (SQL quoting), by the CI readiness check, by test setup and by the shared error classifier. The operator asked to move everything to Psycopg 3 and uninstall `psycopg2`.

## Decision
- **Supabase adapter:** now uses `psycopg.connect` with:
  - `sslmode=verify-full`
  - `prepare_threshold=None`, because the Supabase pooler doesn't keep prepared statements
  - `connection.read_only = True`
  - `dict_row`, and `conninfo_to_dict` for the project/role checks

  The safeguards are unchanged: project and role checks before connecting, a statement timeout, and fixed parameterized catalog queries.
- **Alembic:** `alembic/env.py` rewrites `postgres://`, `postgresql://` or `postgresql+psycopg2://` to `postgresql+psycopg://`, so `.env` URLs need no edit.
  - Migrations `20261011_001` and `20261013_003` import `sql` from `psycopg`. The applied migration `20260807_001` only mentions psycopg2 in a comment and is left as written.
  - CI no longer rewrites the URL scheme.
- **Error handling:** the shared error classifier, CI readiness check and test setup use Psycopg 3. The classifier's psycopg2 branches were removed.
- **Requirements:** `psycopg2-binary` was removed from the gateway and dev requirements and uninstalled from the dev venv.
- **Dev lock file:** `requirements-dev.lock.txt` was regenerated. It now also records packages already installed but missing from it (Psycopg 3, google-auth).
  - The audit found three dev-venv packages behind their fixes, all upgraded: `urllib3` 2.7.0 → 2.8.0, `PyJWT` 2.13.0 → 2.15.1 (matching the gateway pin) and `httpx2` 2.9.1 → 2.13.1.
  - The images were not affected. The mcp SDK accepts any `httpx2` from 2.5.0, so a fresh build installs 2.13.1; the gateway image already pins PyJWT 2.15.1; urllib3 is unpinned.

## Rationale
- One Postgres driver everywhere: less to audit, and one set of behaviour to know.

## Impact
- **Verified 2026-10-13, with psycopg2 uninstalled:**
  - All 8 migrations ran from empty on a disposable pgvector Postgres, and the last 4 were rolled back and re-applied.
  - `alembic current` against Neon reports `20261013_003 (head)`.
  - 150 tests passed, none skipped.
  - The rebuilt gateway image passes `check_image.py` and contains no psycopg2. The document-graph image installs httpx2 2.13.1.
  - pip-audit: no known vulnerabilities in the three image requirement files or the dev lock file.
- **Verified live 2026-10-13:** after the gateway release (`mcp-gateway-00009-8hr`), `gateway_status` and `supabase_list_schema` succeeded from Claude Code through the `horology-tools` plugin.

## Follow-Ups
- None.
