"""Refresh TV2 events poster — used by cron and startup."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from events_display.render import render_events  # noqa: E402


def main():
    render_events()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
