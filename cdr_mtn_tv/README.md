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

Run as **root** on the Pi (idempotent — safe to re-run):

```bash
sudo bash /home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv/scripts/install_pi.sh
```

**Permission model:** root only touches system config (`/etc`, systemd, apt). All git, venv, and app files under `~cdr_mtn_tv` are managed by `app_user_setup.sh` running as `cdr_mtn_tv`. Do not run `git pull` as root in that home directory.

If you only have a root checkout (`/root/WORK/...`), the install script bootstraps the user clone and re-execs from the canonical path above.

To remove systemd units and autologin config (keeps user + repo):

```bash
sudo bash scripts/cleanup.sh
```

The script can be run from any copy of the repo; it installs to `/home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv` by cloning [canteen_calendar](https://github.com/todschmidt/canteen_calendar.git) as the `cdr_mtn_tv` user.

This script:

1. Creates user `cdr_mtn_tv` and installs apt packages (X11, lightdm, feh, git, python venv)
2. Clones or `git pull`s the repo as `cdr_mtn_tv`
3. Creates/updates Python venv and installs dependencies
4. Installs systemd services (run as `cdr_mtn_tv`):
   - `cdr-mtn-tv-startup` — on boot: refresh events + render menu JPGs
   - `cdr-mtn-tv-web` — Flask editor on port 9000 (starts after startup)
5. Configures lightdm autologin → X11 `xsession` → `feh` on `:0.0` (TV1) and `:0.1` (TV2)
6. Adds cron (as `cdr_mtn_tv`): `0 8 * * *` — daily 8 AM events refresh

**Boot order:** `network` → startup (images) → web (editor) → lightdm autologin → feh displays

Access editor from LAN: `http://<pi-ip>:9000/`

### Manual service commands

```bash
sudo systemctl status cdr-mtn-tv-startup
sudo systemctl status cdr-mtn-tv-web
sudo systemctl restart cdr-mtn-tv-startup
sudo systemctl restart lightdm    # restart X + feh displays
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

### X11 / lightdm did not start at boot

Run the diagnostic script on the Pi:

```bash
sudo bash scripts/get_logs.sh
sudo bash scripts/get_logs.sh -f    # follow live logs
```

Checklist (most common first):

1. **Boot target** — must be `graphical.target`: `sudo systemctl set-default graphical.target && sudo reboot`
2. **lightdm running** — `sudo systemctl enable --now lightdm`
3. **X session desktop missing** — install writes `/usr/share/xsessions/cdr-mtn-tv.desktop`; `user-session=cdr-mtn-tv` in lightdm drop-in must match. Re-run `install_pi.sh` if missing.
4. **Wayland vs X11** — feh needs Xorg; Pi OS may default to Wayland on newer images
5. **Session errors** — `~cdr_mtn_tv/.xsession-errors` and `/var/log/Xorg.0.log`
6. **Manual test** — `sudo -u cdr_mtn_tv DISPLAY=:0 /home/cdr_mtn_tv/canteen_calendar/cdr_mtn_tv/scripts/xsession.sh`

### feh not showing on second HDMI

Pi OS often **mirrors** both HDMI outputs at boot. There is one X screen (`:0`), not separate `:0.0` / `:0.1`.

- `configure_displays.sh` runs xrandr extended mode before feh starts
- Both feh windows use `DISPLAY=:0` at `1920x1080+0+0` (TV1) and `1920x1080+1920+0` (TV2)
- Check layout: `DISPLAY=:0 xrandr` (as `cdr_mtn_tv`)
- Check geometry: `cat /run/cdr-mtn-tv/display.env`
- Restart displays: `sudo systemctl restart lightdm`

### Screen blanking / TVs going black

Layered disable is applied by install + xsession:

- lightdm: `xserver-command=X -s 0 -dpms`
- `/etc/X11/xorg.conf.d/99-cdr-mtn-tv-no-blank.conf`
- `disable_blanking.sh` — xset + 5-minute keepalive loop

Check: `DISPLAY=:0 xset q` — DPMS should be Disabled, timeout 0.

If HDMI still blanks, add to `/boot/firmware/config.txt` (Pi firmware): `hdmi_blanking=0` then reboot.

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
