#!/usr/bin/env bash
# Disable screen blanking for 24/7 TV displays.
#
# xset once is not enough on Raspberry Pi — xrandr and drivers may reset DPMS.
# Re-run after configure_displays.sh and after feh starts.
#
# WARNING: "xset dpms force off" turns monitors OFF (requires keypress to wake).
# Use "xset -dpms" to disable power management and "xset dpms force on" to wake.

set -euo pipefail

KEEPALIVE_SEC="${CDR_BLANK_KEEPALIVE_SEC:-300}"

disable_x_blanking() {
  command -v xset >/dev/null 2>&1 || return 0
  export DISPLAY="${DISPLAY:-:0}"
  xset s off 2>/dev/null || true
  xset s noblank 2>/dev/null || true
  xset -dpms 2>/dev/null || true
  xset dpms force on 2>/dev/null || true
}

disable_output_dpms() {
  command -v xrandr >/dev/null 2>&1 || return 0
  export DISPLAY="${DISPLAY:-:0}"
  local out
  while read -r out; do
    [[ -n "${out}" ]] || continue
    xrandr --output "${out}" --set "DPMS" "Disabled" 2>/dev/null || true
  done < <(xrandr --query 2>/dev/null | awk '/ connected/{print $1}')
}

disable_console_blanking() {
  command -v setterm >/dev/null 2>&1 || return 0
  for tty in /dev/tty[0-9]*; do
    setterm -blank 0 -powerdown 0 -powersave off >"${tty}" 2>/dev/null || true
  done
}

disable_x_blanking
disable_output_dpms
disable_console_blanking

# Keep DPMS off for the life of the X session (xrandr resets it periodically).
KEEPALIVE_PID="/run/cdr-mtn-tv/blank-keepalive.pid"
mkdir -p "$(dirname "${KEEPALIVE_PID}")"
if [[ -f "${KEEPALIVE_PID}" ]] && kill -0 "$(cat "${KEEPALIVE_PID}")" 2>/dev/null; then
  exit 0
fi
(
  while true; do
    sleep "${KEEPALIVE_SEC}"
    disable_x_blanking
    disable_output_dpms
  done
) &
echo $! > "${KEEPALIVE_PID}"
