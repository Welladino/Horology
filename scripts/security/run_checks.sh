#!/usr/bin/env bash
# Run the security checks locally and write one report to reports/security/ (replaced on every run).
#
# The same tools, versions and pass rules as Cloud Build (cloudbuild.yaml, scripts/ci/check.sh), plus a
# scan of the Git history for secrets, which Cloud Build can't do (it gets no .git):
#   pip-audit  known vulnerabilities in Python dependencies (dev venv + each requirements.txt)
#   Bandit     Python security linter (.bandit.yaml)
#   Trivy fs   secrets and misconfigurations in the source
#   Trivy      image vulnerabilities and licences (both images, built locally)
#   gitleaks   secrets anywhere in the Git history (redacted in the report)
#
# Usage: scripts/security/run_checks.sh [--skip-images]
# Needs: the dev venv (.venv) and Docker. Exit code 1 if any check would fail Cloud Build.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/reports/security"
TRIVY_IMAGE="aquasec/trivy:0.75.0"      # keep in step with cloudbuild.yaml
GITLEAKS_IMAGE="zricethezav/gitleaks:v8.30.1"
TRIVY_CACHE="$HOME/.cache/horology-trivy"  # vulnerability database, kept between runs
PY="$ROOT/.venv/bin/python"
SKIP_IMAGES=false
[[ "${1:-}" == "--skip-images" ]] && SKIP_IMAGES=true

rm -rf "$OUT" && mkdir -p "$OUT/raw" "$TRIVY_CACHE"
cd "$ROOT" || exit 2
status=()  # "check|exit code" lines for the summary

record() { status+=("$1|$2"); echo "  $1: exit $2"; }
trivy() { docker run --rm -v "$TRIVY_CACHE:/root/.cache/trivy" -v "$SOURCE:/repo:ro" -v "$OUT/raw:/out" "$TRIVY_IMAGE" "$@"; }

# The source scan sees only files Git tracks or would track, like Cloud Build: never .env, .auth/,
# hermes-data/ or the private test clients, which stay on this machine.
SOURCE="$(mktemp -d)"
trap 'rm -rf "$SOURCE"' EXIT
git ls-files -z --cached --others --exclude-standard | while IFS= read -r -d '' file; do
  [[ -f "$file" ]] && mkdir -p "$SOURCE/$(dirname "$file")" && cp -p "$file" "$SOURCE/$file"
done

echo "pip-audit"
"$PY" -m pip_audit -f json -o "$OUT/raw/pip-audit-dev.json" > /dev/null 2>&1; record "pip-audit: dev venv" $?
for req in mcp-servers/mcp-gateway/requirements.txt mcp-servers/document-graph/requirements.txt jobs/document-graph-sync/requirements.txt; do
  name="$(echo "$req" | cut -d/ -f2)"
  "$PY" -m pip_audit --disable-pip --no-deps -r "$req" -f json -o "$OUT/raw/pip-audit-$name.json" > /dev/null 2>&1
  record "pip-audit: $req" $?
done

echo "Bandit"
"$PY" -m bandit -q -c .bandit.yaml -r mcp-servers document-graph-core shared-runtime jobs alembic scripts \
  -f json -o "$OUT/raw/bandit.json" > /dev/null 2>&1; record "Bandit" $?

echo "Trivy: source"
trivy fs --scanners secret,misconfig --severity HIGH,CRITICAL --exit-code 1 --no-progress \
  --format json --output /out/trivy-source.json /repo > /dev/null 2>&1; record "Trivy: source secrets and misconfigurations" $?

if [[ "$SKIP_IMAGES" == false ]]; then
  for image in mcp-gateway document-graph; do
    tag="horology-security/$image:local"
    echo "Image: $image (build, then scan)"
    if ! docker build -q -f "mcp-servers/$image/Dockerfile" -t "$tag" . > /dev/null; then
      record "Build $image image" 1; continue
    fi
    docker save -o "$OUT/raw/$image.tar" "$tag"
    # Blocking in Cloud Build: fixable HIGH/CRITICAL vulnerabilities and secrets.
    trivy image --scanners vuln,secret --ignore-unfixed --severity HIGH,CRITICAL --exit-code 1 --no-progress \
      --format json --output "/out/trivy-$image-vulnerabilities.json" --input "/out/$image.tar" > /dev/null 2>&1
    record "Trivy: $image fixable HIGH/CRITICAL vulnerabilities" $?
    # Every licence, for the report; only "forbidden" ones (CRITICAL, e.g. AGPL) fail.
    trivy image --scanners license --license-full --no-progress \
      --format json --output "/out/trivy-$image-licences.json" --input "/out/$image.tar" > /dev/null 2>&1
    trivy image --scanners license --severity CRITICAL --exit-code 1 --no-progress --quiet \
      --input "/out/$image.tar" > /dev/null 2>&1
    record "Trivy: $image forbidden licences" $?
    rm -f "$OUT/raw/$image.tar"
  done
else
  record "Images (skipped with --skip-images)" skipped
fi

echo "gitleaks: Git history"
docker run --rm -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -v "$ROOT:/repo:ro" -v "$OUT/raw:/out" "$GITLEAKS_IMAGE" git /repo --redact \
  --report-format json --report-path /out/gitleaks.json --no-banner --log-level error > /dev/null 2>&1
record "gitleaks: secrets in Git history" $?

printf '%s\n' "${status[@]}" > "$OUT/raw/status.txt"
"$PY" "$ROOT/scripts/security/summarise.py" "$OUT"
