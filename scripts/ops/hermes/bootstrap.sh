#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
HERMES_DIR="${REPO_ROOT}/hermes"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
COMPOSE_ENV_FILE="${REPO_ROOT}/.env"
CONTAINER="horology-hermes"
HERMES_BIN="/opt/hermes/.venv/bin/hermes"

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

note() {
  printf '%s\n' "$*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

prepare_env_file() {
  local example="$1"
  local target="$2"

  if [[ ! -f "${target}" ]]; then
    cp "${example}" "${target}"
    chmod 600 "${target}"
    note "Created ${target#"${REPO_ROOT}/"} from its example."
    return 0
  fi

  return 1
}

copy_runtime_file() {
  local source="$1"
  local destination="$2"

  docker cp "${source}" "${CONTAINER}:${destination}"
}

copy_skill_group() {
  local source="$1"
  local destination="$2"

  [[ -d "${source}" ]] || die "skill source not found: ${source}"
  # A single skill is copied to its exact destination. A plugin skill group is
  # merged into a shared namespace one skill at a time (horology-tools and
  # horology-document-graph intentionally share one). Clear each skill folder,
  # not the whole group, so removed files do not linger and neighbours survive.
  if [[ -f "${source}/SKILL.md" ]]; then
    docker exec --user root "${CONTAINER}" rm -rf "${destination}"
    docker exec --user root "${CONTAINER}" mkdir -p "${destination}"
    docker cp "${source}/." "${CONTAINER}:${destination}/"
    return
  fi

  local skill_source skill_name skill_destination
  docker exec --user root "${CONTAINER}" mkdir -p "${destination}"
  for skill_source in "${source}"/*; do
    [[ -d "${skill_source}" && -f "${skill_source}/SKILL.md" ]] || continue
    skill_name="$(basename "${skill_source}")"
    skill_destination="${destination}/${skill_name}"
    docker exec --user root "${CONTAINER}" rm -rf "${skill_destination}"
    docker exec --user root "${CONTAINER}" mkdir -p "${skill_destination}"
    docker cp "${skill_source}/." "${CONTAINER}:${skill_destination}/"
  done
}

profile_exists() {
  local profile="$1"
  docker exec --user hermes "${CONTAINER}" test -d "/opt/data/profiles/${profile}"
}

create_profile_if_missing() {
  local profile="$1"
  local description="$2"

  if profile_exists "${profile}"; then
    note "Profile ${profile} already exists."
    return
  fi

  note "Creating profile ${profile}..."
  docker exec --user hermes "${CONTAINER}" \
    "${HERMES_BIN}" profile create "${profile}" --no-alias --description "${description}"
}

require_command docker
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required"

created_env=false
prepare_env_file "${REPO_ROOT}/.env.example" "${COMPOSE_ENV_FILE}" && created_env=true
prepare_env_file "${HERMES_DIR}/.env.example" "${HERMES_DIR}/.env" && created_env=true
prepare_env_file "${HERMES_DIR}/operator/.env.example" "${HERMES_DIR}/operator/.env" && created_env=true
prepare_env_file "${HERMES_DIR}/explorer/.env.example" "${HERMES_DIR}/explorer/.env" && created_env=true

if [[ "${created_env}" == true ]]; then
  cat <<'EOF'

Local .env files were created and remain ignored by Git.
Fill the required values, then run this script again. At minimum, the first
container start requires DASHBOARD_PASSWORD and CRON_SWEEP_RO_DATABASE_URL in
the repository-root .env. Provider, Modal, GitHub and MCP credentials belong
in the profile-specific files shown in hermes/README.md.
EOF
  exit 2
fi

note "Building and starting Hermes..."
if ! docker network inspect horology_default >/dev/null 2>&1; then
  note "Creating the shared horology_default Docker network..."
  docker network create horology_default >/dev/null
fi

docker compose \
  --env-file "${COMPOSE_ENV_FILE}" \
  -f "${COMPOSE_FILE}" \
  up -d --build

docker inspect "${CONTAINER}" >/dev/null 2>&1 || die "${CONTAINER} was not created"

operator_description="Trusted non-code Horology worker for sourced research, browser work, documents, reports, Google workflows, and restricted connected services. Does not execute or modify code or install dependencies."
explorer_description="Isolated code worker for implementation, tests, dependency installation, and unfamiliar repository work in ephemeral Modal sandboxes. No local workspace or credentials unless explicitly imported."

create_profile_if_missing operator "${operator_description}"
create_profile_if_missing explorer "${explorer_description}"

note "Installing reviewed profile configuration..."
for file in SOUL.md .hermes.md config.yaml profile.yaml; do
  copy_runtime_file "${HERMES_DIR}/coordinator/${file}" "/opt/data/${file}"
  copy_runtime_file "${HERMES_DIR}/operator/${file}" "/opt/data/profiles/operator/${file}"
  copy_runtime_file "${HERMES_DIR}/explorer/${file}" "/opt/data/profiles/explorer/${file}"
done

note "Installing local credentials without adding them to Git..."
copy_runtime_file "${HERMES_DIR}/.env" "/opt/data/.env"
copy_runtime_file "${HERMES_DIR}/operator/.env" "/opt/data/profiles/operator/.env"
copy_runtime_file "${HERMES_DIR}/explorer/.env" "/opt/data/profiles/explorer/.env"

note "Installing canonical Horology skills for Coordinator and Operator..."
for profile_root in /opt/data /opt/data/profiles/operator; do
  copy_skill_group "${REPO_ROOT}/plugins/horology-workflows/skills" "${profile_root}/skills/horology-workflows"
  copy_skill_group "${REPO_ROOT}/plugins/horology-specialists/skills" "${profile_root}/skills/horology-specialists"
  copy_skill_group "${REPO_ROOT}/plugins/horology-tools/skills" "${profile_root}/skills/horology-tools"
  copy_skill_group "${REPO_ROOT}/plugins/horology-document-graph/skills" "${profile_root}/skills/horology-tools"
  # The source supervisor is harness-neutral. Install Hermes' adapter in the
  # package-only dispatch path, as the Claude and Codex builders do.
  copy_runtime_file \
    "${REPO_ROOT}/scripts/ops/hermes/horology_supervisor_dispatch.md" \
    "${profile_root}/skills/horology-workflows/horology-supervisor/references/dispatch.md"
done

note "Installing Hermes profile-specific skills..."
copy_skill_group \
  "${REPO_ROOT}/plugins/horology-hermes/skills/horology-coordinator" \
  "/opt/data/skills/horology-hermes/horology-coordinator"
copy_skill_group \
  "${REPO_ROOT}/plugins/horology-hermes/skills/horology-composio-reader" \
  "/opt/data/skills/horology-hermes/horology-composio-reader"
copy_skill_group \
  "${REPO_ROOT}/plugins/horology-hermes/skills/horology-composio-guide" \
  "/opt/data/profiles/operator/skills/horology-hermes/horology-composio-guide"

note "Normalising ownership and selecting Coordinator..."
docker exec --user root "${CONTAINER}" sh -lc \
  'uid="$(id -u hermes)"; gid="$(id -g hermes)"; chown -R "$uid:$gid" /opt/data'
docker exec --user hermes "${CONTAINER}" "${HERMES_BIN}" profile use default

note "Restarting Hermes with the installed configuration..."
docker compose \
  --env-file "${COMPOSE_ENV_FILE}" \
  -f "${COMPOSE_FILE}" \
  restart hermes

cat <<'EOF'

Hermes bootstrap complete.

Next:
  1. Open http://127.0.0.1:9119 and confirm Coordinator, Operator and Explorer.
  2. Complete OAuth login for each enabled OAuth MCP.
  3. Verify the GitHub PAT and Modal credentials using their intended profiles.
  4. Keep all real .env files and generated OAuth tokens out of Git.
EOF
