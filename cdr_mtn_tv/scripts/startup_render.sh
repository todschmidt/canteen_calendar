#!/usr/bin/env bash
# Boot-time image generation for both TVs.
#
# Run order (via systemd cdr-mtn-tv-startup.service, before web + displays):
#   1. refresh_events.py  — fetch events, write output/tv2_events.jpg (needs network)
#   2. menu_display.render — write output/tv1_menu.jpg from data/menu.json (local)
#   3. touch ready marker   — signals the X session it may launch feh
#
# Events refresh may fail offline; menu render still runs. Either failure is non-fatal.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${INSTALL_DIR}/venv/bin/python"
READY="${CDR_MTN_TV_READY:-/run/cdr-mtn-tv/ready}"

mkdir -p "${INSTALL_DIR}/output"
rm -f "${READY}"

cd "${INSTALL_DIR}"

# TV2 first — may require network for the WordPress events API.
"${PYTHON}" scripts/refresh_events.py || true

# TV1 — local menu JSON; always attempt even if events refresh failed.
"${PYTHON}" -m menu_display.render || true

# Tell the graphical session (xsession.sh) that startup images are ready.
mkdir -p "$(dirname "${READY}")"
touch "${READY}"
