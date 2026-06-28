#!/usr/bin/env bash
# Collect diagnostic output when X11 / lightdm / feh fails to start on the Pi.
#
# Usage:
#   bash scripts/get_logs.sh           # one-shot snapshot (works without root)
#   sudo bash scripts/get_logs.sh      # recommended — full journal access
#   sudo bash scripts/get_logs.sh -f   # snapshot then follow lightdm + Xorg logs
#
# Common causes of "X did not start at boot":
#   1. Boot target is multi-user, not graphical  → sudo systemctl set-default graphical.target
#   2. lightdm disabled or not running         → sudo systemctl enable --now lightdm
#   3. user-session name has no .desktop file  → re-run install_pi.sh (installs cdr-mtn-tv.desktop)
#   4. Pi OS booted into Wayland                 → use X11 session; feh requires Xorg
#   5. Another display manager owns the seat     → disable gdm3 / slick-greeter conflicts
#   6. xsession.sh exits immediately             → check ~/.xsession-errors and Xorg log below

set -euo pipefail

APP_USER="cdr_mtn_tv"
HOME_DIR="/home/${APP_USER}"
INSTALL_DIR="${HOME_DIR}/canteen_calendar/cdr_mtn_tv"
LIGHTDM_DROPIN="/etc/lightdm/lightdm.conf.d/50-cdr-mtn-tv.conf"
XSESSION_DESKTOP="/usr/share/xsessions/cdr-mtn-tv.desktop"
SESSION_NAME="cdr-mtn-tv"
READY="/run/cdr-mtn-tv/ready"
LINES="${LINES:-80}"
FOLLOW=false

usage() {
  sed -n '2,7p' "$0" | sed 's/^# \?//'
  echo ""
  echo "Options:"
  echo "  -f, --follow   After snapshot, follow lightdm + Xorg journal (Ctrl+C to stop)"
  echo "  -n N           Journal lines per unit (default: ${LINES})"
  echo "  -h, --help     Show this help"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--follow) FOLLOW=true; shift ;;
    -n) LINES="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

hr() { echo; echo "======================================================================"; echo " $1"; echo "======================================================================"; }

run() {
  echo "+ $*"
  "$@" 2>&1 || echo "  (exit $?)"
}

hr "cdr_mtn_tv diagnostics — $(date -Is 2>/dev/null || date)"

# ---------------------------------------------------------------------------
# Boot / graphical stack
# ---------------------------------------------------------------------------
hr "Boot target"
run systemctl get-default
echo "graphical.target: $(systemctl is-active graphical.target 2>/dev/null || echo unknown)"

hr "Display manager (lightdm)"
run systemctl is-enabled lightdm.service
run systemctl is-active lightdm.service
run systemctl status lightdm.service --no-pager -n 15

# Other DMs can block lightdm from taking the seat
hr "Other display managers (should be inactive/disabled)"
for dm in gdm3 gdm sddm; do
  if systemctl list-unit-files "${dm}.service" >/dev/null 2>&1; then
    echo "${dm}: enabled=$(systemctl is-enabled ${dm}.service 2>/dev/null) active=$(systemctl is-active ${dm}.service 2>/dev/null)"
  fi
done

# ---------------------------------------------------------------------------
# lightdm autologin + X session desktop
# ---------------------------------------------------------------------------
hr "lightdm autologin config"
if [[ -f "${LIGHTDM_DROPIN}" ]]; then
  cat "${LIGHTDM_DROPIN}"
else
  echo "MISSING: ${LIGHTDM_DROPIN}"
  echo "  → re-run: sudo bash ${INSTALL_DIR}/scripts/install_pi.sh"
fi

hr "X session desktop (lightdm user-session must match filename)"
if [[ -f "${XSESSION_DESKTOP}" ]]; then
  cat "${XSESSION_DESKTOP}"
else
  echo "MISSING: ${XSESSION_DESKTOP}"
  echo "  lightdm user-session=${SESSION_NAME} requires this file."
  echo "  → re-run install_pi.sh"
fi

echo ""
echo "Available X sessions in /usr/share/xsessions/:"
ls -1 /usr/share/xsessions/*.desktop 2>/dev/null || echo "  (none found)"

configured_session=""
if [[ -f "${LIGHTDM_DROPIN}" ]]; then
  configured_session=$(grep -E '^user-session=' "${LIGHTDM_DROPIN}" | cut -d= -f2 || true)
fi
echo ""
echo "Configured user-session: ${configured_session:-<not set>}"
if [[ -n "${configured_session}" && ! -f "/usr/share/xsessions/${configured_session}.desktop" ]]; then
  echo "  *** PROBLEM: no /usr/share/xsessions/${configured_session}.desktop ***"
fi

# ---------------------------------------------------------------------------
# User + session files
# ---------------------------------------------------------------------------
hr "User ${APP_USER}"
if id "${APP_USER}" >/dev/null 2>&1; then
  id "${APP_USER}"
  groups "${APP_USER}"
else
  echo "MISSING: user ${APP_USER}"
fi

hr "~${APP_USER}/.xsession (fallback entry)"
if [[ -f "${HOME_DIR}/.xsession" ]]; then
  ls -la "${HOME_DIR}/.xsession"
  cat "${HOME_DIR}/.xsession"
else
  echo "(not present — OK if ${XSESSION_DESKTOP} exists and Exec= points to xsession.sh)"
fi

hr "~${APP_USER}/.xsession-errors (session script failures)"
if [[ -f "${HOME_DIR}/.xsession-errors" ]]; then
  tail -n "${LINES}" "${HOME_DIR}/.xsession-errors"
else
  echo "(no file yet — created when a session starts and stderr is captured)"
fi

# ---------------------------------------------------------------------------
# cdr_mtn_tv systemd services
# ---------------------------------------------------------------------------
hr "cdr_mtn_tv systemd services"
for unit in cdr-mtn-tv-startup cdr-mtn-tv-web; do
  echo "--- ${unit} ---"
  systemctl is-enabled "${unit}.service" 2>/dev/null || echo "  not installed"
  systemctl is-active "${unit}.service" 2>/dev/null || true
  systemctl status "${unit}.service" --no-pager -n 8 2>/dev/null || true
  echo ""
done

# ---------------------------------------------------------------------------
# Journal logs — lightdm, Xorg, session
# ---------------------------------------------------------------------------
hr "journal: lightdm (last ${LINES} lines, this boot)"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -u lightdm.service -b --no-pager -n "${LINES}" 2>/dev/null \
    || journalctl _COMM=lightdm -b --no-pager -n "${LINES}" 2>/dev/null \
    || echo "(no journal access — run with sudo)"
else
  echo "journalctl not available"
fi

hr "journal: Xorg (last ${LINES} lines, this boot)"
if command -v journalctl >/dev/null 2>&1; then
  journalctl -t Xorg -b --no-pager -n "${LINES}" 2>/dev/null \
    || journalctl /usr/lib/xorg/Xorg -b --no-pager -n "${LINES}" 2>/dev/null \
    || echo "(no Xorg journal entries yet)"
fi

hr "/var/log/Xorg.0.log (EE) errors + tail"
XLOG="/var/log/Xorg.0.log"
if [[ -f "${XLOG}" ]]; then
  grep -E '^\(EE\)|error|fatal|no screens' "${XLOG}" 2>/dev/null | tail -n 30 || true
  echo "--- tail ---"
  tail -n 20 "${XLOG}"
else
  echo "(no ${XLOG} — X server may not have started)"
fi

# ---------------------------------------------------------------------------
# Runtime: X display, feh, generated images
# ---------------------------------------------------------------------------
hr "X display + feh processes"
if pgrep -x Xorg >/dev/null 2>&1 || pgrep -x X >/dev/null 2>&1; then
  echo "Xorg is running."
  if id "${APP_USER}" >/dev/null 2>&1; then
    run sudo -u "${APP_USER}" DISPLAY=:0 xrandr --query
  fi
else
  echo "Xorg is NOT running."
fi

echo ""
echo "feh processes:"
pgrep -af "feh.*tv[12]_" 2>/dev/null || echo "  (none)"

hr "Startup marker + output images"
echo "ready marker: ${READY} — $([[ -f ${READY} ]] && echo present || echo missing)"
for f in tv1_menu.jpg tv2_events.jpg; do
  p="${INSTALL_DIR}/output/${f}"
  if [[ -f "${p}" ]]; then
    ls -la "${p}"
  else
    echo "MISSING: ${p}"
  fi
done

hr "refresh.log (last ${LINES} lines)"
REFRESH_LOG="${INSTALL_DIR}/output/refresh.log"
if [[ -f "${REFRESH_LOG}" ]]; then
  tail -n "${LINES}" "${REFRESH_LOG}"
else
  echo "(no ${REFRESH_LOG})"
fi

hr "Manual recovery commands"
cat <<EOF
  sudo systemctl set-default graphical.target
  sudo systemctl enable --now lightdm
  sudo systemctl restart cdr-mtn-tv-startup
  sudo systemctl restart cdr-mtn-tv-web
  sudo systemctl restart lightdm
  # Test session manually (from a root shell):
  sudo -u ${APP_USER} DISPLAY=:0 ${INSTALL_DIR}/scripts/xsession.sh
EOF

# ---------------------------------------------------------------------------
# Follow mode
# ---------------------------------------------------------------------------
if [[ "${FOLLOW}" == true ]]; then
  hr "Following lightdm + Xorg logs (Ctrl+C to stop)"
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Note: follow mode works best with sudo."
  fi
  journalctl -u lightdm.service -f 2>/dev/null &
  pid1=$!
  journalctl -t Xorg -f 2>/dev/null &
  pid2=$!
  trap 'kill ${pid1} ${pid2} 2>/dev/null; exit 0' INT TERM
  wait
fi
