#!/usr/bin/env bash
# Launch feh fullscreen viewers — one per HDMI output.
#
# TV1 (draft menu)  → DISPLAY=:0.0  → output/tv1_menu.jpg
# TV2 (events poster) → DISPLAY=:0.1 → output/tv2_events.jpg
#
# Called by xsession.sh after cdr-mtn-tv-startup.service has generated images.
# feh --reload watches file mtime; editor "Generate" updates propagate automatically.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REFRESH="${CDR_DISPLAY_REFRESH:-30}"

TV1="${INSTALL_DIR}/output/tv1_menu.jpg"
TV2="${INSTALL_DIR}/output/tv2_events.jpg"

mkdir -p "${INSTALL_DIR}/output"

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

# Background both feh instances; wait keeps the X session alive.
DISPLAY=:0.0 feh --fullscreen --auto-zoom --reload "${REFRESH}" "${TV1}" &
DISPLAY=:0.1 feh --fullscreen --auto-zoom --reload "${REFRESH}" "${TV2}" &
wait
