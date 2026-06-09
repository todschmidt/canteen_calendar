#!/usr/bin/env bash
# Idempotent Raspberry Pi setup for cdr_mtn_tv.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(whoami)}"
VENV="${INSTALL_DIR}/venv"
PYTHON="${VENV}/bin/python"
PIP="${VENV}/bin/pip"

echo "=== cdr_mtn_tv Pi install ==="
echo "Install dir: ${INSTALL_DIR}"
echo "User:        ${USER_NAME}"

# 1. Apt dependencies
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y feh python3-venv python3-pip
fi

# 2. Python venv
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
"${PIP}" install -q -r "${INSTALL_DIR}/requirements.txt"

# 3. Output dir + initial renders
mkdir -p "${INSTALL_DIR}/output"
"${PYTHON}" "${INSTALL_DIR}/scripts/refresh_events.py" || true
"${PYTHON}" -m menu_display.render || true

# 4. Make display script executable
chmod +x "${INSTALL_DIR}/scripts/start_displays.sh"

# 5. Install systemd units
SYSTEMD_DIR="/etc/systemd/system"
for unit in cdr-mtn-tv-web cdr-mtn-tv-displays cdr-mtn-tv-refresh; do
  src="${INSTALL_DIR}/scripts/systemd/${unit}.service"
  dest="${SYSTEMD_DIR}/${unit}.service"
  sed -e "s|__INSTALL_DIR__|${INSTALL_DIR}|g" \
      -e "s|__USER__|${USER_NAME}|g" \
      "${src}" | sudo tee "${dest}" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable cdr-mtn-tv-web.service
sudo systemctl enable cdr-mtn-tv-refresh.service
sudo systemctl enable cdr-mtn-tv-displays.service

# 6. Cron — 8 AM daily events refresh
CRON_LINE="0 8 * * * cd ${INSTALL_DIR} && ${PYTHON} scripts/refresh_events.py >> ${INSTALL_DIR}/output/refresh.log 2>&1"
(crontab -l 2>/dev/null | grep -v "scripts/refresh_events.py" || true; echo "${CRON_LINE}") | crontab -

# 7. Start services
sudo systemctl restart cdr-mtn-tv-refresh.service || true
sudo systemctl restart cdr-mtn-tv-web.service || true
sudo systemctl restart cdr-mtn-tv-displays.service || true

echo ""
echo "=== Install complete ==="
echo "Editor:  http://$(hostname -I | awk '{print $1}'):9000/"
echo "Services:"
echo "  sudo systemctl status cdr-mtn-tv-web"
echo "  sudo systemctl status cdr-mtn-tv-displays"
echo "  sudo systemctl status cdr-mtn-tv-refresh"
