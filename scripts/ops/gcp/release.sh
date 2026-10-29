#!/usr/bin/env bash
# One-command release of the MCP services to Cloud Run (horology-dev).
#
#   scripts/ops/gcp/release.sh document-graph   # service + sync job
#   scripts/ops/gcp/release.sh gateway
#   scripts/ops/gcp/release.sh all
#
# Options: --migrate (apply pending Alembic revisions first), --yes (no
# confirmation before deploying), --dry-run (print the commands, run nothing).
# Steps follow docs/runbook/gcp/mcp_deployment.md. Runs on macOS bash 3.2.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

PROJECT="horology-dev"
REGION="us-central1"
REPOSITORY="mcp-servers"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}"
SERVICE_URL_SUFFIX="366292507424.${REGION}.run.app"
DEPLOY_CONFIG="horology"
ADMIN_CONFIG="horology-admin"
SYNC_JOB="document-graph-sync"
BUILD_SA="projects/${PROJECT}/serviceAccounts/mcp-build@${PROJECT}.iam.gserviceaccount.com"
STAGING_DIR="gs://${PROJECT}-mcp-build-source/source"

DRY_RUN=0
MIGRATE=0
ASSUME_YES=0
TARGET=""

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '%s\n' "$*"
}

step() {
  printf '\n== %s\n' "$*"
}

usage() {
  sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

# Runs a command, or only prints it with --dry-run.
run() {
  if [[ "${DRY_RUN}" == 1 ]]; then
    printf '+ %s\n' "$*"
    return 0
  fi
  "$@"
}

gcloud_deploy() {
  run gcloud --configuration="${DEPLOY_CONFIG}" "$@" --project="${PROJECT}"
}

gcloud_admin() {
  run gcloud --configuration="${ADMIN_CONFIG}" "$@" --project="${PROJECT}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run) DRY_RUN=1 ;;
      --migrate) MIGRATE=1 ;;
      --yes|-y) ASSUME_YES=1 ;;
      -h|--help) usage 0 ;;
      gateway|document-graph|all)
        [[ -z "${TARGET}" ]] || die "give one target, not '${TARGET}' and '$1'"
        TARGET="$1"
        ;;
      *) die "unknown argument: $1 (try --help)" ;;
    esac
    shift
  done
  [[ -n "${TARGET}" ]] || usage 1
}

wants() {
  [[ "${TARGET}" == all || "${TARGET}" == "$1" ]]
}

services() {
  if wants gateway; then printf '%s\n' mcp-gateway; fi
  if wants document-graph; then printf '%s\n' document-graph; fi
}

# Succeeds when the configuration can get a token, including any service
# account it impersonates; otherwise prints gcloud's reason.
signed_in() {
  local reason
  if reason="$(gcloud --configuration="$1" auth print-access-token 2>&1 >/dev/null)"; then
    return 0
  fi
  printf '%s\n' "${reason}" | grep -m1 'ERROR' >&2 || true
  return 1
}

preflight() {
  step "Preflight"
  cd "${REPO_ROOT}"
  # macOS privacy protection makes reads under ~/Documents fail with
  # "Operation not permitted" when the terminal app lacks Documents access.
  head -c 1 cloudbuild.yaml >/dev/null 2>&1 \
    || die "can't read cloudbuild.yaml. On macOS, give your terminal app access to the Documents folder (System Settings > Privacy & Security > Files & Folders), then reopen it."

  # The Cloud Build upload has no .git, and its tests dry-run this script.
  if git rev-parse --git-dir >/dev/null 2>&1; then
    local branch
    branch="$(git rev-parse --abbrev-ref HEAD)"
    [[ "${branch}" == main ]] || note "warning: releasing from branch '${branch}', not main"
    [[ -z "$(git status --porcelain)" ]] || note "warning: uncommitted changes will be included in the build upload"
    note "Commit: $(git rev-parse --short HEAD) on ${branch}"
  else
    note "warning: not a git checkout; branch and commit not checked"
  fi

  if [[ "${DRY_RUN}" == 1 ]]; then
    return 0
  fi
  command -v gcloud >/dev/null 2>&1 || die "gcloud not found"
  command -v python3 >/dev/null 2>&1 || die "python3 not found"
  signed_in "${DEPLOY_CONFIG}" \
    || die "gcloud configuration '${DEPLOY_CONFIG}' can't get a token (see above). It signs in as its core/account and impersonates horology-deployer: docs/runbook/gcp/operator_checks.md"
  if wants document-graph; then
    signed_in "${ADMIN_CONFIG}" \
      || die "gcloud configuration '${ADMIN_CONFIG}' can't get a token (see above); it's needed for the sync job"
  fi
  note "gcloud configurations signed in."
}

check_migrations() {
  step "Database migrations"
  local alembic=(.venv/bin/dotenv -f .env run -- .venv/bin/python -m alembic)
  if [[ "${DRY_RUN}" == 1 ]]; then
    run "${alembic[@]}" current
    [[ "${MIGRATE}" == 1 ]] && run "${alembic[@]}" upgrade head
    return 0
  fi
  [[ -x .venv/bin/dotenv && -f .env ]] || die "needs the repo .venv and the root .env with the owner DATABASE_URL"

  local current
  current="$("${alembic[@]}" current 2>/dev/null | tail -1)"
  if [[ "${current}" == *"(head)"* ]]; then
    note "Neon is at head: ${current}"
    return 0
  fi
  note "Neon is behind: '${current:-no revision}'; head is $(.venv/bin/python -m alembic heads 2>/dev/null | tail -1)"
  [[ "${MIGRATE}" == 1 ]] || die "pending migrations. Check they are safe for the running revisions, then rerun with --migrate"
  "${alembic[@]}" upgrade head
}

record_revisions() {
  step "Serving revisions (for rollback)"
  local svc
  for svc in $(services); do
    if [[ "${DRY_RUN}" == 1 ]]; then
      run gcloud --configuration="${DEPLOY_CONFIG}" run services describe "${svc}" --project="${PROJECT}" --region="${REGION}"
      continue
    fi
    note "${svc}: $(gcloud --configuration="${DEPLOY_CONFIG}" run services describe "${svc}" \
      --project="${PROJECT}" --region="${REGION}" --format='value(status.latestReadyRevisionName)')"
  done
}

BUILD_ID=""

build() {
  step "Cloud Build (tests, images, scans)"
  if [[ "${DRY_RUN}" == 1 ]]; then
    gcloud_deploy builds submit . --config=cloudbuild.yaml --async \
      --gcs-source-staging-dir="${STAGING_DIR}" --service-account="${BUILD_SA}"
    BUILD_ID="BUILD_ID"
    return 0
  fi

  BUILD_ID="$(gcloud --configuration="${DEPLOY_CONFIG}" builds submit . --project="${PROJECT}" \
    --config=cloudbuild.yaml --async --format='value(id)' \
    --gcs-source-staging-dir="${STAGING_DIR}" --service-account="${BUILD_SA}")"
  [[ -n "${BUILD_ID}" ]] || die "Cloud Build didn't return a build ID"
  note "Build ${BUILD_ID} submitted. Logs: gcloud --configuration=${DEPLOY_CONFIG} builds log ${BUILD_ID} --project=${PROJECT}"

  local status="" last=""
  while :; do
    status="$(gcloud --configuration="${DEPLOY_CONFIG}" builds describe "${BUILD_ID}" \
      --project="${PROJECT}" --format='value(status)')"
    [[ "${status}" == "${last}" ]] || note "  $(date +%H:%M:%S) ${status}"
    last="${status}"
    case "${status}" in
      SUCCESS) return 0 ;;
      QUEUED|PENDING|WORKING) sleep 20 ;;
      *) die "build ${BUILD_ID} ended ${status}; see the log command above. Nothing was deployed." ;;
    esac
  done
}

# Prints the sha256 digest Cloud Build pushed for one image.
digest_for() {
  local image="$1"
  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'sha256:DIGEST\n'
    return 0
  fi
  gcloud --configuration="${DEPLOY_CONFIG}" builds describe "${BUILD_ID}" --project="${PROJECT}" \
    --format='json(results.images)' | python3 -c '
import json, sys
want = sys.argv[1]
for image in json.load(sys.stdin).get("results", {}).get("images", []):
    if image.get("name") == want:
        print(image["digest"])
        break
' "${REGISTRY}/${image}:${BUILD_ID}"
}

confirm() {
  [[ "${ASSUME_YES}" == 1 || "${DRY_RUN}" == 1 ]] && return 0
  local answer
  printf '\nDeploy to %s? [y/N] ' "${PROJECT}"
  read -r answer
  [[ "${answer}" == y || "${answer}" == Y ]] || die "stopped before deploying; build ${BUILD_ID} is kept in the registry"
}

deploy() {
  local svc="$1" digest="$2"
  local image="${REGISTRY}/${svc}@${digest}"
  step "Deploy ${svc}"
  gcloud_deploy run services update "${svc}" --region="${REGION}" --image="${image}"
  if [[ "${svc}" == document-graph ]]; then
    gcloud_admin run jobs update "${SYNC_JOB}" --region="${REGION}" --image="${image}"
  fi
}

expect_status() {
  local expected="$1" label="$2"
  shift 2
  if [[ "${DRY_RUN}" == 1 ]]; then
    run curl -s -o /dev/null -w '%{http_code}' "$@"
    return 0
  fi
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$@")"
  if [[ "${code}" == "${expected}" ]]; then
    note "  ok   ${label}: ${code}"
  else
    note "  FAIL ${label}: ${code}, expected ${expected}"
    return 1
  fi
}

verify() {
  local svc="$1" base="https://$1-${SERVICE_URL_SUFFIX}"
  step "Check ${svc}"
  expect_status 200 "OAuth discovery" "${base}/.well-known/oauth-authorization-server" \
    && expect_status 401 "anonymous MCP" -X POST "${base}/mcp" -H 'Content-Type: application/json' -d '{}'
}

# Moves deployed-current with tags.patch: the deployer may update tags but not
# delete them, so `gcloud artifacts docker tags add` fails on an existing tag.
# The token goes to curl on stdin, never on the command line.
move_deployed_tag() {
  local svc="$1" digest="$2"
  local package="projects/${PROJECT}/locations/${REGION}/repositories/${REPOSITORY}/packages/${svc}"
  local version="${package}/versions/${digest}"
  step "Tag ${svc} deployed-current"
  if [[ "${DRY_RUN}" == 1 ]]; then
    run curl -X PATCH "https://artifactregistry.googleapis.com/v1/${package}/tags/deployed-current?updateMask=version"
    return 0
  fi
  local reply
  reply="$(gcloud --configuration="${DEPLOY_CONFIG}" auth print-access-token \
    | sed 's/^/Authorization: Bearer /' \
    | curl -sS -X PATCH -H @- -H 'Content-Type: application/json' \
        -d "{\"version\": \"${version}\"}" \
        "https://artifactregistry.googleapis.com/v1/${package}/tags/deployed-current?updateMask=version")"
  if printf '%s' "${reply}" | python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("version") != sys.argv[1])' "${version}" 2>/dev/null; then
    note "deployed-current -> ${digest}"
  else
    note "warning: couldn't move deployed-current for ${svc}; move it by hand (docs/runbook/gcp/cloud_build.md)"
    return 1
  fi
}

main() {
  parse_args "$@"
  [[ "${DRY_RUN}" == 1 ]] && note "Dry run: printing commands only."
  preflight
  check_migrations
  record_revisions
  build

  local svc digest digests=""
  for svc in $(services); do
    digest="$(digest_for "${svc}")"
    [[ "${digest}" == sha256:* ]] || die "no digest for ${svc} in build ${BUILD_ID}"
    note "${svc}: ${digest}"
    digests="${digests}${svc}=${digest} "
  done
  confirm

  local failed=0 pair
  for pair in ${digests}; do
    svc="${pair%%=*}"
    digest="${pair#*=}"
    deploy "${svc}" "${digest}"
    if verify "${svc}"; then
      move_deployed_tag "${svc}" "${digest}" || failed=1
    else
      failed=1
      note "Roll back: gcloud --configuration=${DEPLOY_CONFIG} run services update-traffic ${svc} --project=${PROJECT} --region=${REGION} --to-revisions=PREVIOUS_REVISION=100 (revision printed above)"
    fi
  done

  step "Done"
  note "Build ${BUILD_ID}."
  [[ "${failed}" == 0 ]] || die "a check or the tag move failed; see above"
  note "Next: reconnect the client and call list_documents (and gateway_status for the gateway)."
}

main "$@"
