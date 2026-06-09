# cdr_mtn_tv — Implementation Checklist

## Phase 1 — Scaffold

- [x] Directory structure (`assets/`, `data/`, `output/`, `web/`, `scripts/`)
- [x] `config.json` with group/column `width_percent`
- [x] `requirements.txt`, `data/menu.json`
- [x] `paths.py` shared helpers

## Phase 2 — Assets

- [x] Copy header, footer, arialbd from source project
- [x] Bundle Oswald + Merriweather fonts in `assets/fonts/`

## Phase 3 — Image Renderers

- [x] `events_display/render.py` — TV2 portrait poster
- [x] `menu_display/render.py` — TV1 landscape table
- [x] `scripts/refresh_events.py` — cron/startup entry point

## Phase 4 — Flask Web App

- [x] `web/app.py` — single process, `--role` flag, `threaded=False`
- [x] `editor.html` — menu form + Generate button
- [x] `events.html` — streamed events stub with breadcrumb
- [x] `display.html` — auto-refresh img (debug TV1/TV2)
- [x] `_nav.html` breadcrumb partial

## Phase 5 — Debug & Pi Deploy

- [x] `scripts/debug_launcher.py` — 3 Flask subprocesses
- [x] `scripts/install_pi.sh` — idempotent Pi setup
- [x] `scripts/start_displays.sh` — feh dual-HDMI launcher
- [x] systemd unit templates

## Phase 6 — Documentation

- [x] `README.md` with delimited sections
- [x] `PLAN.md`
- [x] `PROMPTS.md`

## Future (TBD)

- [ ] Streamed-events actions on `/events` page
- [ ] Menu layout/styling refinements
- [ ] Pi HDMI positioning validation on hardware
- [ ] Optional Chromium fallback testing
