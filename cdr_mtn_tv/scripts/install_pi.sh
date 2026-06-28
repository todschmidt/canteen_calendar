#!/usr/bin/env bash
# Idempotent Raspberry Pi production install for cdr_mtn_tv.
#
# MUST be run as root:
#   sudo bash /home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv/scripts/install_pi.sh
#
# Permission model:
#   ROOT  — apt, useradd, /etc (systemd, lightdm), systemctl; rm poisoned ~cdr_mtn_tv clones only
#   cdr_mtn_tv — all repo, venv, app files via app_user_setup.sh (never sudo -i)
#
# Invoked from /root/WORK/...? Re-execs immediately to the canonical script (runs once).

set -euo pipefail

APP_USER="cdr_mtn_tv"
HOME_DIR="/home/${APP_USER}"
REPO_DIR="${HOME_DIR}/canteen_calendar"
INSTALL_DIR="${REPO_DIR}/cdr_mtn_tv"
VENV="${INSTALL_DIR}/venv"
PYTHON="${VENV}/bin/python"
SYSTEMD_DIR="/etc/systemd/system"
LIGHTDM_DROPIN="/etc/lightdm/lightdm.conf.d/50-cdr-mtn-tv.conf"
XSESSION_DESKTOP="/usr/share/xsessions/cdr-mtn-tv.desktop"
SESSION_NAME="cdr-mtn-tv"
CANONICAL="${INSTALL_DIR}/scripts/install_pi.sh"
APP_SETUP="${INSTALL_DIR}/scripts/app_user_setup.sh"
GIT_CHECK="${INSTALL_DIR}/scripts/git_repo_check.sh"
REPO_URL="https://github.com/todschmidt/canteen_calendar.git"

# Never sudo -i — login shells source .bashrc and may cd or export GIT_* for /root/WORK.
run_as_user() {
  sudo -u "${APP_USER}" env HOME="${HOME_DIR}" "$@"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root: sudo bash $0" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Re-exec first — avoid running apt/setup twice when called from /root/WORK
# ---------------------------------------------------------------------------
THIS="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
if [[ -f "${CANONICAL}" ]]; then
  TARGET="$(readlink -f "${CANONICAL}" 2>/dev/null || realpath "${CANONICAL}" 2>/dev/null || echo "${CANONICAL}")"
  if [[ "${THIS}" != "${TARGET}" ]]; then
    echo "NOTE: invoked ${THIS}"
    echo "      re-exec → ${CANONICAL}"
    exec env CDR_MTN_TV_INSTALL=1 bash "${CANONICAL}"
  fi
fi

echo "=== cdr_mtn_tv Pi install (root) ==="
echo "App user:    ${APP_USER}"
echo "Install dir: ${INSTALL_DIR}"

# ---------------------------------------------------------------------------
# 1. Application user
# ---------------------------------------------------------------------------
if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "--- Creating user ${APP_USER} ---"
  useradd -m -s /bin/bash "${APP_USER}"
fi

usermod -aG video,input,render,tty "${APP_USER}" 2>/dev/null || \
  usermod -aG video,input,tty "${APP_USER}" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 2. Minimal X11 + lightdm
# ---------------------------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
  echo "--- Installing apt packages (minimal X11 + lightdm) ---"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    feh git python3-venv python3-pip \
    xserver-xorg-core xserver-xorg \
    xserver-xorg-input-all xserver-xorg-video-all \
    x11-common x11-xserver-utils xinit dbus-x11 \
    lightdm openbox
  systemctl enable lightdm.service 2>/dev/null || true
  systemctl set-default graphical.target 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 3. Ensure a healthy user-owned clone (root deletes poisoned trees only)
# ---------------------------------------------------------------------------
ensure_user_repo() {
  git_repo_poisoned_local() {
    local d="${REPO_DIR}"
    [[ -L "${d}" ]] && return 0
    [[ -f "${d}/.git" ]] && grep -q '/root/' "${d}/.git" 2>/dev/null && return 0
    [[ -f "${d}/.git/config" ]] && grep -qE '(^|\s)/root/' "${d}/.git/config" 2>/dev/null && return 0
    return 1
  }

  if [[ -f "${GIT_CHECK}" ]]; then
    # shellcheck source=git_repo_check.sh
    source "${GIT_CHECK}"
  else
    git_repo_poisoned() { git_repo_poisoned_local; }
  fi

  if [[ -e "${REPO_DIR}" ]] && { git_repo_poisoned "${REPO_DIR}" || ! run_as_user git -C "${REPO_DIR}" status >/dev/null 2>&1; }; then
    echo "--- Removing root-poisoned repo at ${REPO_DIR} ---"
    rm -rf "${REPO_DIR}"
  fi

  if ! run_as_user git -C "${REPO_DIR}" status >/dev/null 2>&1; then
    echo "--- Cloning repository (as ${APP_USER}) ---"
    run_as_user git clone "${REPO_URL}" "${REPO_DIR}"
  fi
}

ensure_user_repo

# ---------------------------------------------------------------------------
# 4. App setup — entirely as cdr_mtn_tv
# ---------------------------------------------------------------------------
echo "--- App setup (as ${APP_USER}) ---"
run_as_user bash "${APP_SETUP}"

# ---------------------------------------------------------------------------
# 5. X autologin session files
# ---------------------------------------------------------------------------
echo "--- Configuring X autologin ---"

cat > "${HOME_DIR}/.xsession" <<EOF
#!/bin/sh
# Managed by install_pi.sh — re-run install to regenerate.
exec ${INSTALL_DIR}/scripts/xsession.sh
EOF
chown "${APP_USER}:${APP_USER}" "${HOME_DIR}/.xsession"
chmod 755 "${HOME_DIR}/.xsession"

mkdir -p /etc/lightdm/lightdm.conf.d
cat > "${LIGHTDM_DROPIN}" <<EOF
# Managed by install_pi.sh
[Seat:*]
autologin-user=${APP_USER}
autologin-user-timeout=0
user-session=${SESSION_NAME}
EOF

cat > "${XSESSION_DESKTOP}" <<EOF
[Desktop Entry]
Name=cdr_mtn_tv
Comment=Cedar Mountain Canteen TV displays (feh on dual HDMI)
Exec=${INSTALL_DIR}/scripts/xsession.sh
Type=XSession
DesktopNames=cdr_mtn_tv
TryExec=${INSTALL_DIR}/scripts/xsession.sh
EOF

# ---------------------------------------------------------------------------
# 6. systemd units
# ---------------------------------------------------------------------------
echo "--- Installing systemd units ---"

for legacy in cdr-mtn-tv-refresh cdr-mtn-tv-displays; do
  systemctl disable --now "${legacy}.service" 2>/dev/null || true
  rm -f "${SYSTEMD_DIR}/${legacy}.service"
done

for unit in cdr-mtn-tv-startup cdr-mtn-tv-web; do
  sed -e "s|__INSTALL_DIR__|${INSTALL_DIR}|g" \
      -e "s|__USER__|${APP_USER}|g" \
      "${INSTALL_DIR}/scripts/systemd/${unit}.service" \
      > "${SYSTEMD_DIR}/${unit}.service"
done

systemctl daemon-reload
systemctl enable cdr-mtn-tv-startup.service cdr-mtn-tv-web.service

# ---------------------------------------------------------------------------
# 7. Cron
# ---------------------------------------------------------------------------
CRON_LINE="0 8 * * * cd ${INSTALL_DIR} && ${PYTHON} scripts/refresh_events.py >> ${INSTALL_DIR}/output/refresh.log 2>&1"
(
  run_as_user crontab -l 2>/dev/null | grep -v "scripts/refresh_events.py" || true
  echo "${CRON_LINE}"
) | run_as_user crontab -

# ---------------------------------------------------------------------------
# 8. Start services
# ---------------------------------------------------------------------------
echo "--- Starting services ---"
systemctl restart cdr-mtn-tv-startup.service
systemctl restart cdr-mtn-tv-web.service
systemctl restart lightdm.service 2>/dev/null || true

echo ""
echo "=== Install complete ==="
echo "Install dir: ${INSTALL_DIR}"
echo "Editor:      http://$(hostname -I | awk '{print $1}'):9000/"
echo ""
echo "Re-run anytime: sudo bash ${CANONICAL}"
