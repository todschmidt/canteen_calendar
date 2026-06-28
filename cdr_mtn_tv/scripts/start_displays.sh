#!/usr/bin/env bash
# Launch feh viewers — one per HDMI output on an extended :0 desktop.
#
# TV1 (draft menu)   → geometry 1920x1080+0+0
# TV2 (events poster) → geometry 1920x1080+1920+0
#
# configure_displays.sh must run first (xsession.sh) to disable mirror mode.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REFRESH="${CDR_DISPLAY_REFRESH:-30}"
DISPLAY_ENV="/run/cdr-mtn-tv/display.env"
export DISPLAY="${DISPLAY:-:0}"

TV1="${INSTALL_DIR}/output/tv1_menu.jpg"
TV2="${INSTALL_DIR}/output/tv2_events.jpg"

mkdir -p "${INSTALL_DIR}/output"

if [[ -f "${DISPLAY_ENV}" ]]; then
  # shellcheck source=/dev/null
  source "${DISPLAY_ENV}"
fi
: "${DISPLAY:=:0}"
: "${TV1_GEOM:=1920x1080+0+0}"
: "${TV2_GEOM:=1920x1080+1920+0}"

# Placeholder images if startup_render has not yet produced real output.
if [[ ! -f "$TV1" ]]; then
  convert -size 1920x1080 xc:'#202020' "$TV1" 2>/dev/null || \
    python3 -c "
from PIL import Image
Image.new('RGB', (1920, 1080), (32, 32, 32)).save('${TV1}')
"
fi
if [[ ! -f "$TV2" ]]; then
  convert -size 1920x1080 xc:'#202020' "$TV2" 2>/dev/null || \
    python3 -c "
from PIL import Image
Image.new('RGB', (1920, 1080), (32, 32, 32)).save('${TV2}')
"
fi

launch_feh() {
  if [[ -f "${DISPLAY_ENV}" ]]; then
    # shellcheck source=/dev/null
    source "${DISPLAY_ENV}"
  fi
  : "${DISPLAY:=:0}"
  : "${TV1_GEOM:=1920x1080+0+0}"
  : "${TV2_GEOM:=1920x1080+1920+0}"
  pkill -x feh 2>/dev/null || true
  sleep 0.5
  DISPLAY="${DISPLAY}" feh --borderless --auto-zoom --reload "${REFRESH}" \
    --geometry "${TV1_GEOM}" "${TV1}" &
  DISPLAY="${DISPLAY}" feh --borderless --auto-zoom --reload "${REFRESH}" \
    --geometry "${TV2_GEOM}" "${TV2}" &
}

launch_feh

# If only one HDMI was up at session start, reconfigure when the second appears.
if [[ "${DUAL_HDMI:-0}" != "1" ]]; then
  (
    for _ in $(seq 1 60); do
      sleep 5
      "${INSTALL_DIR}/scripts/configure_displays.sh" || true
      if [[ -f "${DISPLAY_ENV}" ]]; then
        # shellcheck source=/dev/null
        source "${DISPLAY_ENV}"
      fi
      [[ "${DUAL_HDMI:-0}" == "1" ]] || continue
      echo "start_displays: second HDMI ready — relaunching feh" >&2
      launch_feh
      break
    done
  ) &
fi

wait
