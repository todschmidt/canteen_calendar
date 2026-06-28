#!/usr/bin/env bash
# Graphical session entry point for the cdr_mtn_tv user (called from ~/.xsession).
#
# Boot sequence this script participates in:
#   1. systemd multi-user.target
#   2. cdr-mtn-tv-startup.service  — generates JPGs, writes /run/cdr-mtn-tv/ready
#   3. cdr-mtn-tv-web.service      — Flask editor on port 9000
#   4. lightdm autologin → wait for ready + HDMI → configure_displays → feh
#
# Dual HDMI uses xrandr extended desktop, not separate :0.0 / :0.1 screens.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
READY="/run/cdr-mtn-tv/ready"
export DISPLAY="${DISPLAY:-:0}"

# Disable screen blanking (X11 + console); keepalive loop runs in background.
"${INSTALL_DIR}/scripts/disable_blanking.sh" || true

# Wait for systemd startup_render.sh (up to 120 s).
# Run this BEFORE configure_displays — cold boot needs time for network + HDMI.
if [[ ! -f "${READY}" ]]; then
  echo "xsession: waiting for ${READY} ..." >&2
  for _ in $(seq 1 120); do
    [[ -f "${READY}" ]] && break
    sleep 1
  done
fi

# Extended dual-HDMI (disable mirror) after startup + HDMI enumeration.
"${INSTALL_DIR}/scripts/configure_displays.sh" || true

# Minimal window manager — feh fullscreen windows still benefit from a WM session.
if command -v openbox >/dev/null 2>&1; then
  openbox &
fi

exec "${INSTALL_DIR}/scripts/start_displays.sh"
