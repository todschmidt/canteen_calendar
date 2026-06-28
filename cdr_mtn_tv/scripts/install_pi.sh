#!/usr/bin/env bash
# Idempotent Raspberry Pi production install for cdr_mtn_tv.
#
# MUST be run as root:
#   sudo bash /home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv/scripts/install_pi.sh
#
# Permission model:
#   ROOT  — apt, useradd, /etc (systemd, lightdm), systemctl; never git/chmod in ~cdr_mtn_tv
#   cdr_mtn_tv — all repo, venv, and app files via app_user_setup.sh
#
# If invoked from a root-owned checkout (e.g. /root/WORK/...), bootstraps the user repo
# then re-execs itself from the canonical install path.

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
APP_SETUP="${INSTALL_DIR}/scripts/app_user_setup.sh"

run_as_user() {
  sudo -u "${APP_USER}" HOME="${HOME_DIR}" "$@"
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root: sudo bash $0" >&2
  exit 1
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
# 2. Minimal X11 + lightdm (feh requires Xorg, not Wayland)
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
# 3. Bootstrap clone (git as cdr_mtn_tv only) so app_user_setup.sh exists
# ---------------------------------------------------------------------------
if ! run_as_user test -d "${REPO_DIR}/.git"; then
  echo "--- Initial clone (as ${APP_USER}) ---"
  run_as_user git clone "https://github.com/todschmidt/canteen_calendar.git" "${REPO_DIR}"
fi

# ---------------------------------------------------------------------------
# 4. Re-exec from canonical path if invoked from a root-owned checkout
# ---------------------------------------------------------------------------
CANONICAL="${INSTALL_DIR}/scripts/install_pi.sh"
THIS="$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")"
TARGET="$(readlink -f "${CANONICAL}" 2>/dev/null || realpath "${CANONICAL}" 2>/dev/null || echo "${CANONICAL}")"

if [[ "${THIS}" != "${TARGET}" ]]; then
  echo "NOTE: invoked ${THIS}"
  echo "      re-exec → ${CANONICAL}"
  exec bash "${CANONICAL}"
fi

# ---------------------------------------------------------------------------
# 5. Repo, venv, app files — entirely as cdr_mtn_tv (never root in ~cdr_mtn_tv)
# ---------------------------------------------------------------------------
echo "--- App setup (as ${APP_USER}) ---"
run_as_user bash "${APP_SETUP}"

# ---------------------------------------------------------------------------
# 6. X autologin session files
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
# 7. systemd units (system paths — root only)
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
# 8. Cron (as cdr_mtn_tv)
# ---------------------------------------------------------------------------
CRON_LINE="0 8 * * * cd ${INSTALL_DIR} && ${PYTHON} scripts/refresh_events.py >> ${INSTALL_DIR}/output/refresh.log 2>&1"
(
  run_as_user crontab -l 2>/dev/null | grep -v "scripts/refresh_events.py" || true
  echo "${CRON_LINE}"
) | run_as_user crontab -

# ---------------------------------------------------------------------------
# 9. Start services
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
