#!/usr/bin/env bash
# Graphical session entry point for the cdr_mtn_tv user (called from ~/.xsession).
#
# Boot sequence this script participates in:
#   1. systemd multi-user.target
#   2. cdr-mtn-tv-startup.service  — generates JPGs, writes /run/cdr-mtn-tv/ready
#   3. cdr-mtn-tv-web.service      — Flask editor on port 9000
#   4. lightdm autologin → this script → start_displays.sh (feh on :0.0 and :0.1)
#
# feh requires X11 (not Wayland). lightdm must use user-session=xsession for this user.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
READY="/run/cdr-mtn-tv/ready"
TV1="${INSTALL_DIR}/output/tv1_menu.jpg"
TV2="${INSTALL_DIR}/output/tv2_events.jpg"

# Disable screen blanking so menu/events stay visible 24/7.
xset s off
xset -dpms
xset s noblank

# Optional: configure dual HDMI outputs before feh starts.
# Uncomment and adjust for your wiring if :0.0 / :0.1 are not assigned as expected.
# xrandr --output HDMI-1 --primary --mode 1920x1080 --pos 0x0
# xrandr --output HDMI-2 --mode 1920x1080 --pos 1920x0

# Wait for systemd startup_render.sh (up to 120 s). Fall through if marker missing
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
