#!/usr/bin/env bash
# Remove cdr_mtn_tv systemd units, lightdm autologin config, and related cron.
#
# MUST be run as root:
#   sudo bash scripts/cleanup.sh
#
# Use before re-running install_pi.sh on a machine with a legacy layout, or to
# fully tear down automated services while leaving the cdr_mtn_tv user + repo intact.
#
# Removes:
#   - systemd units: cdr-mtn-tv-startup, cdr-mtn-tv-web (current)
#   - systemd units: cdr-mtn-tv-refresh, cdr-mtn-tv-displays (legacy)
#   - lightdm drop-in: /etc/lightdm/lightdm.conf.d/50-cdr-mtn-tv.conf
#   - X session desktop: /usr/share/xsessions/cdr-mtn-tv.desktop
#   - crontab entry for scripts/refresh_events.py (cdr_mtn_tv user)
#
# Does NOT remove:
#   - cdr_mtn_tv user account or home directory
#   - cloned repository or generated output images
#   - apt packages (xserver-xorg, lightdm, feh, etc.)

set -euo pipefail

APP_USER="cdr_mtn_tv"
HOME_DIR="/home/${APP_USER}"
INSTALL_DIR="${HOME_DIR}/canteen_calendar/cdr_mtn_tv"
SYSTEMD_DIR="/etc/systemd/system"
LIGHTDM_DROPIN="/etc/lightdm/lightdm.conf.d/50-cdr-mtn-tv.conf"
XSESSION_DESKTOP="/usr/share/xsessions/cdr-mtn-tv.desktop"

# All known unit names — current and legacy install layouts
UNITS=(
  cdr-mtn-tv-startup
  cdr-mtn-tv-web
  cdr-mtn-tv-refresh
  cdr-mtn-tv-displays
)

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root: sudo bash $0" >&2
  exit 1
fi

echo "=== cdr_mtn_tv cleanup ==="

# Stop and disable every cdr-mtn-tv systemd unit that may exist
for unit in "${UNITS[@]}"; do
  if systemctl list-unit-files "${unit}.service" >/dev/null 2>&1; then
    echo "--- Stopping ${unit}.service ---"
    systemctl stop "${unit}.service" 2>/dev/null || true
    systemctl disable "${unit}.service" 2>/dev/null || true
  fi
  if [[ -f "${SYSTEMD_DIR}/${unit}.service" ]]; then
    echo "--- Removing ${SYSTEMD_DIR}/${unit}.service ---"
    rm -f "${SYSTEMD_DIR}/${unit}.service"
  fi
done

systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true

# lightdm autologin drop-in written by install_pi.sh
if [[ -f "${LIGHTDM_DROPIN}" ]]; then
  echo "--- Removing ${LIGHTDM_DROPIN} ---"
  rm -f "${LIGHTDM_DROPIN}"
fi

if [[ -f "${XSESSION_DESKTOP}" ]]; then
  echo "--- Removing ${XSESSION_DESKTOP} ---"
  rm -f "${XSESSION_DESKTOP}"
fi

# X session entry point for autologin (legacy fallback)
if [[ -f "${HOME_DIR}/.xsession" ]]; then
  echo "--- Removing ${HOME_DIR}/.xsession ---"
  rm -f "${HOME_DIR}/.xsession"
fi

# Daily events refresh cron (cdr_mtn_tv user only)
if id "${APP_USER}" >/dev/null 2>&1; then
  if sudo -u "${APP_USER}" crontab -l 2>/dev/null | grep -q "scripts/refresh_events.py"; then
    echo "--- Removing refresh_events cron for ${APP_USER} ---"
    sudo -u "${APP_USER}" crontab -l 2>/dev/null \
      | grep -v "scripts/refresh_events.py" \
      | sudo -u "${APP_USER}" crontab - 2>/dev/null || true
  fi
fi

# Stop any feh viewers still running from a previous X session
if pgrep -u "${APP_USER}" -f "feh.*tv[12]_" >/dev/null 2>&1; then
  echo "--- Stopping feh display processes for ${APP_USER} ---"
  pkill -u "${APP_USER}" -f "feh.*tv1_menu.jpg" 2>/dev/null || true
  pkill -u "${APP_USER}" -f "feh.*tv2_events.jpg" 2>/dev/null || true
fi

# Restart lightdm so autologin config changes take effect (ignore if not running)
systemctl restart lightdm.service 2>/dev/null || true

echo ""
echo "=== Cleanup complete ==="
echo "Removed systemd units, lightdm drop-in, .xsession, and refresh cron."
echo "Repo left at: ${INSTALL_DIR}"
echo "Re-install with: sudo bash ${INSTALL_DIR}/scripts/install_pi.sh"
