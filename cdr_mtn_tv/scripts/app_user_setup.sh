#!/usr/bin/env bash
# Application setup run entirely as cdr_mtn_tv — NEVER as root.
#
# Called by install_pi.sh:
#   sudo -u cdr_mtn_tv env HOME=/home/cdr_mtn_tv bash .../app_user_setup.sh
#
# No login shell (no sudo -i) — avoids .bashrc cd/GIT_* pointing at /root/WORK.

set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "ERROR: do not run as root. install_pi.sh invokes this as cdr_mtn_tv." >&2
  exit 1
fi

REPO_URL="https://github.com/todschmidt/canteen_calendar.git"
REPO_DIR="${HOME}/canteen_calendar"
INSTALL_DIR="${REPO_DIR}/cdr_mtn_tv"
VENV="${INSTALL_DIR}/venv"
PIP="${VENV}/bin/pip"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=git_repo_check.sh
source "${SCRIPT_DIR}/git_repo_check.sh"

echo "=== cdr_mtn_tv app setup (user: $(whoami), HOME=${HOME}) ==="
echo "Repo dir:    ${REPO_DIR}"
echo "Install dir: ${INSTALL_DIR}"

reclaim_repo() {
  if [[ -e "${REPO_DIR}" ]]; then
    echo "WARN: reclaiming ${REPO_DIR} (broken or root-poisoned git metadata)"
    rm -rf "${REPO_DIR}" || {
      echo "ERROR: cannot remove ${REPO_DIR}; as root run: rm -rf ${REPO_DIR}" >&2
      exit 1
    }
  fi
  git clone "${REPO_URL}" "${REPO_DIR}"
}

echo "--- Syncing repository ---"
if git_repo_healthy "${REPO_DIR}"; then
  cd "${REPO_DIR}"
  git config core.fileMode false
  if ! git pull --ff-only; then
    echo "WARN: pull failed; resetting to origin/main"
    git fetch origin
    git reset --hard origin/main
  fi
else
  reclaim_repo
  cd "${REPO_DIR}"
  git config core.fileMode false
fi

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: missing ${INSTALL_DIR} after sync" >&2
  exit 1
fi

cd "${INSTALL_DIR}"

echo "--- Python venv ---"
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
"${PIP}" install -q -r requirements.txt

mkdir -p output

chmod +x \
  scripts/install_pi.sh \
  scripts/app_user_setup.sh \
  scripts/git_repo_check.sh \
  scripts/start_displays.sh \
  scripts/xsession.sh \
  scripts/startup_render.sh \
  scripts/cleanup.sh \
  scripts/get_logs.sh

echo "=== App setup complete ==="
