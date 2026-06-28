#!/usr/bin/env bash
# Idempotent Raspberry Pi production install for cdr_mtn_tv.
#
# MUST be run as root:
#   sudo bash scripts/install_pi.sh
#
# What this script does:
#   1. Creates dedicated system user `cdr_mtn_tv`
#   2. Installs apt packages (X11, lightdm, feh, python venv, git)
#   3. Clones or updates https://github.com/todschmidt/canteen_calendar.git as cdr_mtn_tv
#   4. Creates Python venv + installs requirements under cdr_mtn_tv/canteen_calendar/cdr_mtn_tv
#   5. Installs systemd units (startup → web) running as cdr_mtn_tv
#   6. Configures lightdm autologin → X11 session → xsession.sh → feh displays
#   7. Installs daily cron for events refresh (8 AM)
#
# Boot / start order:
#   network-online.target
#     → cdr-mtn-tv-startup.service  (refresh_events + menu render, touch /run/cdr-mtn-tv/ready)
#     → cdr-mtn-tv-web.service      (Flask editor :9000)
#   graphical.target
#     → lightdm autologin cdr_mtn_tv
#     → ~/.xsession → xsession.sh (waits for ready marker)
#     → start_displays.sh (feh on :0.0 and :0.1)
#
# Assumptions:
#   - Raspberry Pi OS or Debian-based Pi image with systemd
#   - Two HDMI outputs mapped to X screens :0.0 and :0.1 (see xsession.sh xrandr notes)
#   - X11 session (feh does not run on Wayland)

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — canonical install paths
# ---------------------------------------------------------------------------
APP_USER="cdr_mtn_tv"
REPO_URL="https://github.com/todschmidt/canteen_calendar.git"
HOME_DIR="/home/${APP_USER}"
REPO_DIR="${HOME_DIR}/canteen_calendar"
INSTALL_DIR="${REPO_DIR}/cdr_mtn_tv"
VENV="${INSTALL_DIR}/venv"
PYTHON="${VENV}/bin/python"
PIP="${VENV}/bin/pip"
SYSTEMD_DIR="/etc/systemd/system"
LIGHTDM_DROPIN="/etc/lightdm/lightdm.conf.d/50-cdr-mtn-tv.conf"

# ---------------------------------------------------------------------------
# Preflight — root only
# ---------------------------------------------------------------------------
if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root: sudo bash $0" >&2
  exit 1
fi

echo "=== cdr_mtn_tv Pi install ==="
echo "User:        ${APP_USER}"
echo "Repo:        ${REPO_URL}"
echo "Install dir: ${INSTALL_DIR}"

# ---------------------------------------------------------------------------
# 1. Dedicated application user
# ---------------------------------------------------------------------------
if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "--- Creating user ${APP_USER} ---"
  useradd -m -s /bin/bash "${APP_USER}"
else
  echo "--- User ${APP_USER} already exists ---"
fi

# GPU / input access for X and feh on Raspberry Pi
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
    xserver-xorg-core \
    xserver-xorg \
    xserver-xorg-input-all \
    xserver-xorg-video-all \
    x11-common \
    x11-xserver-utils \
    xinit \
    dbus-x11 \
    lightdm \
    openbox
  # Ensure lightdm starts on boot (graphical login → cdr_mtn_tv autologin)
  systemctl enable lightdm.service 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 3. Clone or update repository as APP_USER (never as root)
# ---------------------------------------------------------------------------
echo "--- Syncing repository ---"
if [[ -d "${REPO_DIR}/.git" ]]; then
  sudo -u "${APP_USER}" git -C "${REPO_DIR}" pull --ff-only
else
  sudo -u "${APP_USER}" git clone "${REPO_URL}" "${REPO_DIR}"
fi

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "ERROR: expected app at ${INSTALL_DIR} after clone" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. Python venv + dependencies (as APP_USER)
# ---------------------------------------------------------------------------
echo "--- Python venv ---"
if [[ ! -d "${VENV}" ]]; then
  sudo -u "${APP_USER}" python3 -m venv "${VENV}"
fi
sudo -u "${APP_USER}" "${PIP}" install -q -r "${INSTALL_DIR}/requirements.txt"

mkdir -p "${INSTALL_DIR}/output"
chown -R "${APP_USER}:${APP_USER}" "${HOME_DIR}"

# ---------------------------------------------------------------------------
# 5. Executable helper scripts
# ---------------------------------------------------------------------------
chmod +x \
  "${INSTALL_DIR}/scripts/start_displays.sh" \
  "${INSTALL_DIR}/scripts/xsession.sh" \
  "${INSTALL_DIR}/scripts/startup_render.sh" \
  "${INSTALL_DIR}/scripts/cleanup.sh"

# ---------------------------------------------------------------------------
# 6. X session autostart for APP_USER (lightdm → .xsession → xsession.sh)
# ---------------------------------------------------------------------------
echo "--- Configuring X autologin session ---"

# .xsession is the entry lightdm invokes for user-session=xsession
cat > "${HOME_DIR}/.xsession" <<EOF
#!/bin/sh
# Managed by install_pi.sh — do not edit by hand; re-run install to regenerate.
exec ${INSTALL_DIR}/scripts/xsession.sh
EOF
chown "${APP_USER}:${APP_USER}" "${HOME_DIR}/.xsession"
chmod +x "${HOME_DIR}/.xsession"

# lightdm drop-in: autologin APP_USER into X11 xsession (not Wayland)
mkdir -p /etc/lightdm/lightdm.conf.d
cat > "${LIGHTDM_DROPIN}" <<EOF
# Managed by install_pi.sh — autologin cdr_mtn_tv into X11 feh display session
[Seat:*]
autologin-user=${APP_USER}
autologin-user-timeout=0
user-session=xsession
EOF

# ---------------------------------------------------------------------------
# 7. systemd units — startup before web; displays via X session (not systemd)
# ---------------------------------------------------------------------------
echo "--- Installing systemd units ---"

# Retire legacy units from earlier install layouts
for legacy in cdr-mtn-tv-refresh cdr-mtn-tv-displays; do
  systemctl disable --now "${legacy}.service" 2>/dev/null || true
  rm -f "${SYSTEMD_DIR}/${legacy}.service"
done

for unit in cdr-mtn-tv-startup cdr-mtn-tv-web; do
  src="${INSTALL_DIR}/scripts/systemd/${unit}.service"
  dest="${SYSTEMD_DIR}/${unit}.service"
  sed -e "s|__INSTALL_DIR__|${INSTALL_DIR}|g" \
      -e "s|__USER__|${APP_USER}|g" \
      "${src}" > "${dest}"
done

systemctl daemon-reload
systemctl enable cdr-mtn-tv-startup.service
systemctl enable cdr-mtn-tv-web.service

# ---------------------------------------------------------------------------
# 8. Cron — daily 8 AM events refresh (as APP_USER)
# ---------------------------------------------------------------------------
CRON_LINE="0 8 * * * cd ${INSTALL_DIR} && ${PYTHON} scripts/refresh_events.py >> ${INSTALL_DIR}/output/refresh.log 2>&1"
(
  sudo -u "${APP_USER}" crontab -l 2>/dev/null | grep -v "scripts/refresh_events.py" || true
  echo "${CRON_LINE}"
) | sudo -u "${APP_USER}" crontab -

# ---------------------------------------------------------------------------
# 9. Run startup + enable services; restart graphical session if already running
# ---------------------------------------------------------------------------
echo "--- Starting services ---"
systemctl restart cdr-mtn-tv-startup.service
systemctl restart cdr-mtn-tv-web.service

# Restart lightdm so autologin + xsession take effect (ignore if no display attached)
systemctl restart lightdm.service 2>/dev/null || true

echo ""
echo "=== Install complete ==="
echo "Install dir: ${INSTALL_DIR}"
echo "Editor:      http://$(hostname -I | awk '{print $1}'):9000/"
echo ""
echo "Boot order:"
echo "  1. cdr-mtn-tv-startup  — generate TV1/TV2 JPGs"
echo "  2. cdr-mtn-tv-web      — menu editor"
echo "  3. lightdm autologin   — X session → feh on :0.0 + :0.1"
echo ""
echo "Useful commands:"
echo "  systemctl status cdr-mtn-tv-startup"
echo "  systemctl status cdr-mtn-tv-web"
echo "  journalctl -u cdr-mtn-tv-startup -u cdr-mtn-tv-web -e"
echo "  sudo -u ${APP_USER} crontab -l"
