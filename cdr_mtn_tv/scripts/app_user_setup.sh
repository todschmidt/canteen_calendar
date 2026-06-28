#!/usr/bin/env bash
# Application setup run entirely as cdr_mtn_tv — NEVER as root.
#
# Called by install_pi.sh:
#   sudo -u cdr_mtn_tv bash /home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv/scripts/app_user_setup.sh
#
# Handles everything under ~cdr_mtn_tv that must not be touched by root:
#   git clone / pull, venv, pip, output dir, script permissions.

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

echo "=== cdr_mtn_tv app setup (user: $(whoami)) ==="
echo "Repo dir:    ${REPO_DIR}"
echo "Install dir: ${INSTALL_DIR}"

git config --global core.fileMode false

repo_ok() {
  [[ -d "${REPO_DIR}/.git" ]] && [[ -r "${INSTALL_DIR}/scripts/install_pi.sh" ]]
}

echo "--- Syncing repository ---"
if repo_ok; then
  cd "${REPO_DIR}"
  if ! git pull --ff-only; then
    echo "WARN: pull failed; resetting to origin/main"
    git fetch origin
    git reset --hard origin/main
  fi
else
  if [[ -e "${REPO_DIR}" ]]; then
    echo "WARN: ${REPO_DIR} unusable; moving aside"
    mv "${REPO_DIR}" "${REPO_DIR}.bak.$(date +%s)"
  fi
  git clone "${REPO_URL}" "${REPO_DIR}"
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
  scripts/start_displays.sh \
  scripts/xsession.sh \
  scripts/startup_render.sh \
  scripts/cleanup.sh \
  scripts/get_logs.sh

echo "=== App setup complete ==="
