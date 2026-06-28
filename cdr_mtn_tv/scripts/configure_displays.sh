#!/usr/bin/env bash
# Put dual HDMI outputs into extended (side-by-side) mode for feh.
#
# Raspberry Pi OS often boots with mirrored HDMI. Modern X uses one screen (:0)
# and xrandr positions each output — there is no separate :0.1 screen.
#
# Writes geometry for start_displays.sh to:
#   /run/cdr-mtn-tv/display.env

set -euo pipefail

OUT_FILE="/run/cdr-mtn-tv/display.env"
W="${CDR_DISPLAY_WIDTH:-1920}"
H="${CDR_DISPLAY_HEIGHT:-1080}"

mkdir -p "$(dirname "${OUT_FILE}")"

# Connected outputs in xrandr order (usually HDMI-A-1, HDMI-A-2 on Pi 4/5).
mapfile -t OUTPUTS < <(xrandr --query | awk '/ connected/{print $1}')

if [[ ${#OUTPUTS[@]} -lt 2 ]]; then
  echo "configure_displays: ${#OUTPUTS[@]} output(s) — using single-screen layout" >&2
  cat > "${OUT_FILE}" <<EOF
DISPLAY=:0
TV1_GEOM=${W}x${H}+0+0
TV2_GEOM=
EOF
  exit 0
fi

OUT1="${OUTPUTS[0]}"
OUT2="${OUTPUTS[1]}"

echo "configure_displays: ${OUT1} (TV1 left) + ${OUT2} (TV2 right) @ ${W}x${H}" >&2

# Extended desktop: TV1 at 0,0 — TV2 immediately to the right (un-mirror).
xrandr --output "${OUT1}" --primary --mode "${W}x${H}" --pos 0x0 2>/dev/null \
  || xrandr --output "${OUT1}" --primary --auto --pos 0x0

xrandr --output "${OUT2}" --mode "${W}x${H}" --pos "${W}x0" --right-of "${OUT1}" 2>/dev/null \
  || xrandr --output "${OUT2}" --auto --right-of "${OUT1}"

cat > "${OUT_FILE}" <<EOF
DISPLAY=:0
TV1_GEOM=${W}x${H}+0+0
TV2_GEOM=${W}x${H}+${W}+0
OUT1=${OUT1}
OUT2=${OUT2}
EOF
