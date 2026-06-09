# cdr_mtn_tv

Dual-TV display system for Cedar Mountain Canteen — draft/food menu on TV1 (landscape) and events poster on TV2 (portrait).

<<<SECTION:OVERVIEW>>>

## Overview

Runs on a Raspberry Pi 4 with two 1080p HDMI outputs:

| TV | Resolution | Content | Update method |
|----|------------|---------|---------------|
| TV1 | 1920×1080 landscape | Draft & food menu table | Web editor → Generate button |
| TV2 | 1920×1080 (rendered portrait, rotated −90°) | This Week + Upcoming events poster | Daily 8 AM cron + startup refresh |

**Pi production:** TVs use `feh` to display JPG files directly (lightweight, no browser on TVs).

**Debug mode (Windows/local):** Three Flask subprocesses on ports 9000/9001/9002 serve the editor and auto-refreshing image viewer pages.

<<<END_SECTION>>>

<<<SECTION:QUICKSTART_DEBUG>>>

## Quick Start — Debug Mode

```bash
cd cdr_mtn_tv
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

# Generate initial images
python -m menu_display.render
python scripts/refresh_events.py

# Start 3 Flask subprocesses (no threads)
python scripts/debug_launcher.py
```

Open in browser:

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:9000/ | Menu editor |
| http://127.0.0.1:9000/events | Streamed events (stub) |
| http://127.0.0.1:9001/tv1 | TV1 display preview |
| http://127.0.0.1:9002/tv2 | TV2 display preview |

Edit menu values, click **Save**, then **Generate TV1 Image**. Display pages auto-refresh every 30 seconds.

<<<END_SECTION>>>

<<<SECTION:PI_INSTALL>>>

## Raspberry Pi Installation

Idempotent install script — safe to re-run:

```bash
cd cdr_mtn_tv
chmod +x scripts/install_pi.sh
./scripts/install_pi.sh
```

This script:

1. Installs `feh`, `python3-venv`
2. Creates/updates Python venv and installs dependencies
3. Generates initial menu and events images
4. Installs systemd services:
   - `cdr-mtn-tv-web` — Flask editor on port 9000
   - `cdr-mtn-tv-displays` — two `feh` instances (TV1 on `:0.0`, TV2 on `:0.1`)
   - `cdr-mtn-tv-refresh` — events refresh on boot
5. Adds cron: `0 8 * * *` — daily 8 AM events refresh
6. Enables and starts all services

Access editor from LAN: `http://<pi-ip>:9000/`

### Manual service commands

```bash
sudo systemctl status cdr-mtn-tv-web
sudo systemctl status cdr-mtn-tv-displays
sudo systemctl restart cdr-mtn-tv-displays
```

### Chromium fallback (optional)

If `feh` cannot target the second HDMI, use Chromium kiosk on a minimal auto-refresh page:

```bash
chromium-browser --kiosk --app=http://localhost:9001/tv1
```

Requires running debug-style display ports or adding display routes to the editor service. Not the default.

<<<END_SECTION>>>

<<<SECTION:CONFIG>>>

## Configuration

All settings in [`config.json`](config.json):

| Key | Purpose |
|-----|---------|
| `events_api_url` | WordPress events REST endpoint |
| `tv1` / `tv2` | Output image dimensions (`tv2` renders 1080×1920 canvas, saves rotated per `rotate_degrees`) |
| `assets.events_header` | Events poster header image (`header.png`) |
| `menu_groups` | Draft/Food group labels and `width_percent` (must sum to 100) |
| `menu_columns` | Column keys, labels, group, `width_percent` within group |
| `fonts` | TTF paths for header, body, fallback |
| `placeholders` | Default header/footer text |
| `display_refresh_seconds` | Image poll interval (debug pages + feh `--reload`) |
| `ports` | Debug mode ports: editor 9000, tv1 9001, tv2 9002 |
| `cron_schedule` | Documented cron expression (`0 8 * * *`) |

Editable menu content is stored in [`data/menu.json`](data/menu.json).

<<<END_SECTION>>>

<<<SECTION:FONTS>>>

## Fonts

Bundled in `assets/fonts/` (Google Fonts, OFL license):

| Font | Role |
|------|------|
| **Merriweather** | Header/footer — warm serif |
| **Oswald** | Table body — condensed pub-menu style |
| **arialbd.ttf** | Fallback if variable fonts fail |

Other fonts to consider: **Lora** (food descriptions), **Bebas Neue** (large titles), **Patrick Hand** (bakery chalkboard accents).

<<<END_SECTION>>>

<<<SECTION:TROUBLESHOOTING>>>

## Troubleshooting

### feh not showing on second HDMI

- Verify dual outputs: `xrandr`
- Check `DISPLAY=:0.0` and `DISPLAY=:0.1` in `scripts/start_displays.sh`
- Ensure graphical session is running before `cdr-mtn-tv-displays` starts

### TV2 events not updating

- Check cron: `crontab -l`
- Manual refresh: `python scripts/refresh_events.py`
- Check log: `output/refresh.log`

### TV1 not updating after Generate

- Confirm `output/tv1_menu.jpg` mtime changed
- feh `--reload 30` picks up file changes automatically

### Flask editor not reachable

- `sudo systemctl status cdr-mtn-tv-web`
- Check port: `ss -tlnp | grep 9000`

<<<END_SECTION>>>
