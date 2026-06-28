#!/usr/bin/env bash
# Graphical session entry point for the cdr_mtn_tv user (called from ~/.xsession).
#
# Boot sequence this script participates in:
#   1. systemd multi-user.target
#   2. cdr-mtn-tv-startup.service  — generates JPGs, writes /run/cdr-mtn-tv/ready
#   3. cdr-mtn-tv-web.service      — Flask editor on port 9000
#   4. lightdm autologin → configure_displays.sh → start_displays.sh (feh on :0)
#
# Dual HDMI uses xrandr extended desktop, not separate :0.0 / :0.1 screens.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
READY="/run/cdr-mtn-tv/ready"
TV1="${INSTALL_DIR}/output/tv1_menu.jpg"
TV2="${INSTALL_DIR}/output/tv2_events.jpg"

# Disable screen blanking so menu/events stay visible 24/7.
xset s off
xset -dpms
xset s noblank

# Extended dual-HDMI (disable mirror) before feh starts.
"${INSTALL_DIR}/scripts/configure_displays.sh"

# Wait for systemd startup_render.sh (up to 120 s).
# but placeholder images exist — start_displays.sh can create blanks.
if [[ ! -f "${READY}" ]]; then
  echo "xsession: waiting for ${READY} ..."
  for _ in $(seq 1 120); do
    [[ -f "${READY}" ]] && break
    sleep 1
  done
fi

# Minimal window manager — feh fullscreen windows still benefit from a WM session.
if command -v openbox >/dev/null 2>&1; then
  openbox &
fi

exec "${INSTALL_DIR}/scripts/start_displays.sh"
