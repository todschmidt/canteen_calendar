# cdr_mtn_tv — Architecture Plan

## Goal

Single-use Raspberry Pi 4 dual-HDMI display system:

- **TV1 (1920×1080 landscape):** Editable draft/food menu → static JPG
- **TV2 (1920×1080 after −90° rotation):** This Week / Upcoming events poster from WordPress API
- **Debug mode:** Three browser windows on ports 9000/9001/9002
- **Future:** Streamed-events actions on `/events` page (stub in v1)

## Architecture

```mermaid
flowchart LR
  subgraph flask [Flask - Port 9000]
    Editor[editor.html]
    EventsPage[events.html stub]
    Editor <-->|breadcrumb| EventsPage
    Editor -->|"Generate"| MenuRender[menu_display/render.py]
    MenuRender --> TV1JPG[output/tv1_menu.jpg]
  end

  subgraph debugDisplays [Debug - Ports 9001/9002]
    TV1Page["display.html img refresh"]
    TV2Page["display.html img refresh"]
    TV1JPG --> TV1Page
    TV2JPG[output/tv2_events.jpg] --> TV2Page
  end

  subgraph piDisplays [Pi Production - feh]
    FehTV1["feh --reload 30 tv1_menu.jpg"]
    FehTV2["feh --reload 30 tv2_events.jpg"]
    TV1JPG --> FehTV1
    TV2JPG --> FehTV2
  end

  subgraph refresh [TV2 Refresh]
    Cron["cron 8:00 AM"]
    Startup["startup on boot"]
    EventsRender[events_display/render.py]
    WPAPI[WordPress API]
    Cron --> EventsRender
    Startup --> EventsRender
    WPAPI --> EventsRender
    EventsRender --> TV2JPG
  end
```

## Design Decisions

| Decision | Choice |
|----------|--------|
| Pi TV display | feh fullscreen with `--reload 30` |
| Debug TV display | Minimal display.html with cache-busted img |
| Flask concurrency | No threads — subprocess launcher for debug |
| Web UI | Separate editor.html + events.html with breadcrumb |
| TV2 refresh | Cron 8 AM + startup refresh on boot |
| Pi setup | Idempotent install_pi.sh |
| Config | menu_groups + menu_columns width_percent |
| Chromium | Optional fallback only |

## Display Refresh

| Context | Mechanism |
|---------|-----------|
| Pi feh | `--reload 30` detects JPG mtime change |
| Debug browser | JS setInterval reloads img with `?t=timestamp` |

No WebSockets, no Flask threads, no push notifications.

## Non-Goals (v1)

- Authentication
- Multi-tenant / reusable framework
- Dynamic HTML menus on TVs
- Streamed-events actions (stub only)
