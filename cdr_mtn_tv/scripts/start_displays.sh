#!/usr/bin/env bash
# Spawn feh viewers for TV1 (landscape) and TV2 (portrait).
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REFRESH="${CDR_DISPLAY_REFRESH:-30}"

TV1="${INSTALL_DIR}/output/tv1_menu.jpg"
TV2="${INSTALL_DIR}/output/tv2_events.jpg"

mkdir -p "${INSTALL_DIR}/output"

# Placeholder images if not yet generated
if [[ ! -f "$TV1" ]]; then
  convert -size 1920x1080 xc:'#202020' "$TV1" 2>/dev/null || \
    python3 -c "
from PIL import Image
Image.new('RGB', (1920, 1080), (32,32,32)).save('${TV1}')
"
fi
if [[ ! -f "$TV2" ]]; then
  convert -size 1920x1080 xc:'#202020' "$TV2" 2>/dev/null || \
    python3 -c "
from PIL import Image
Image.new('RGB', (1920, 1080), (32,32,32)).save('${TV2}')
"
fi

DISPLAY=:0.0 feh --fullscreen --auto-zoom --reload "${REFRESH}" "${TV1}" &
DISPLAY=:0.1 feh --fullscreen --auto-zoom --reload "${REFRESH}" "${TV2}" &
