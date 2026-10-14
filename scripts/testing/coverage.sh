#!/usr/bin/env bash
# Measure test coverage and write a report to reports/coverage/ (replaced on every run).
#
# A view of what the tests exercise, not a gate: there's no minimum percentage.
# Unit tests always run; integration tests run when the disposable database variables are set
# (GRAPH_TEST_RUNTIME_URL, GATEWAY_TEST_DATABASE_URL, GATEWAY_TEST_RUNTIME_URL), otherwise they are
# skipped and their code shows as uncovered. System (Docker) tests are left out: they test the
# containers, not our Python code.
#
# Usage: scripts/testing/coverage.sh
# Open reports/coverage/html/index.html for line-by-line detail.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/reports/coverage"
cd "$ROOT" || exit 2
rm -rf "$OUT" && mkdir -p "$OUT"

if [[ -n "${GRAPH_TEST_RUNTIME_URL:-}" && -n "${GATEWAY_TEST_DATABASE_URL:-}" ]]; then
  kinds="unit and integration tests"
else
  kinds="unit tests only (integration skipped: no test database variables)"
fi

COVERAGE_FILE="$OUT/.coverage" "$ROOT/.venv/bin/python" -m pytest tests/unit tests/integration -q -p no:cacheprovider \
  --cov=document-graph-core/graph_core --cov=shared-runtime/horology_runtime \
  --cov=mcp-servers/mcp-gateway --cov=mcp-servers/document-graph --cov=jobs/document-graph-sync \
  --cov-branch --cov-report=term-missing:skip-covered --cov-report="html:$OUT/html" --cov-report="xml:$OUT/coverage.xml" \
  > "$OUT/pytest.txt" 2>&1
code=$?

{
  echo "# Test coverage — $(date '+%Y-%m-%d %H:%M')"
  echo
  echo "Replaced on every run of scripts/testing/coverage.sh. Measured with $kinds."
  echo "Line-by-line detail: html/index.html. Tests: $(tail -1 "$OUT/pytest.txt")"
  echo
  echo '```'
  sed -n '/^Name /,/^TOTAL/p' "$OUT/pytest.txt"
  echo '```'
  echo
  echo "Files at 100% are left out of the table above."
} > "$OUT/summary.md"

echo "Report: $OUT/summary.md (detail: $OUT/html/index.html)"
grep -E "^TOTAL" "$OUT/pytest.txt"
exit $code
