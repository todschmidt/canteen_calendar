#!/usr/bin/env bash
# Disable screen blanking for 24/7 TV displays.
#
# xset once is not enough on Raspberry Pi — DPMS may reset. This script applies
# X11 settings immediately and re-applies every 5 minutes in the background.

set -euo pipefail

KEEPALIVE_SEC="${CDR_BLANK_KEEPALIVE_SEC:-300}"

disable_x_blanking() {
  command -v xset >/dev/null 2>&1 || return 0
  export DISPLAY="${DISPLAY:-:0}"
  xset s off
  xset s noblank
  xset -dpms
  xset dpms force off 2>/dev/null || true
}

disable_console_blanking() {
  # Separate from X11 — affects Linux virtual consoles.
  command -v setterm >/dev/null 2>&1 || return 0
  for tty in /dev/tty[0-9]*; do
    setterm -blank 0 -powerdown 0 -powersave off >"${tty}" 2>/dev/null || true
  done
}

disable_x_blanking
disable_console_blanking

# Keep DPMS off for the life of the X session.
(
  while true; do
    sleep "${KEEPALIVE_SEC}"
    disable_x_blanking
  done
) &
