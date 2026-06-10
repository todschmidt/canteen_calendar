"""Render TV2 events poster from WordPress API."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from pprint import pp
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import load_config, root_path  # noqa: E402

# Canvas dimensions (portrait) — rotated for final TV output.
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
FONT_SIZE = 36
TITLE_FONT_SIZE = int(FONT_SIZE * 1.15)
SECTION_FONT_SIZE = 48
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
LINE_HEIGHT = FONT_SIZE + 15
TITLE_LINE_HEIGHT = TITLE_FONT_SIZE + 15
THIS_WEEK_SLOT_COUNT = 5

TIGHTEN_PX = 15
SECTION_HEADING_GAP_AFTER = LINE_HEIGHT - 15
_EVENT_ROW_SPACING_BASE = int(CANVAS_HEIGHT * 0.018) + 35
EVENT_ROW_SPACING = int(_EVENT_ROW_SPACING_BASE * 0.3 * 0.8)
INTER_SECTION_GAP = max(
    _EVENT_ROW_SPACING_BASE, _EVENT_ROW_SPACING_BASE * 2 - 50
)
SECTION_DIVIDER_WIDTH = 2
SECTION_DIVIDER_PADDING = 12

DAY_ABBREV = {
    0: "Mon",
    1: "Tues",
    2: "Wed",
    3: "Thurs",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def scaled_gap(base_gap, tighten_px=TIGHTEN_PX):
    return int(base_gap * (1 - tighten_px / base_gap))


def expanded_gap(base_gap, widen_px):
    return int(base_gap * (1 + widen_px / base_gap))


_THIS_WEEK_GAP_DAY_TIME = 220
_THIS_WEEK_GAP_TIME_TITLE = scaled_gap(200)
THIS_WEEK_TIME_X = LEFT_MARGIN + _THIS_WEEK_GAP_DAY_TIME
THIS_WEEK_TITLE_X = THIS_WEEK_TIME_X + _THIS_WEEK_GAP_TIME_TITLE

_UPCOMING_GAP_DAY_DATE = expanded_gap(90, 25)
_UPCOMING_GAP_DATE_TIME = scaled_gap(160)
_UPCOMING_GAP_TIME_TITLE = 190
UPCOMING_DATE_X = LEFT_MARGIN + _UPCOMING_GAP_DAY_DATE
UPCOMING_TIME_X = UPCOMING_DATE_X + _UPCOMING_GAP_DATE_TIME
UPCOMING_TITLE_X = UPCOMING_TIME_X + _UPCOMING_GAP_TIME_TITLE


def wrap_text(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [text]
    lines = []
    current_line = words[0]
    for word in words[1:]:
        test_line = f"{current_line} {word}"
        if draw.textlength(test_line, font=font) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines


def format_time_compact(dt):
    hour = dt.hour % 12 or 12
    suffix = "am" if dt.hour < 12 else "pm"
    if dt.minute == 0:
        return f"{hour}{suffix}"
    return f"{hour}:{dt.minute:02d}{suffix}"


def format_date_slash(dt):
    return f"{dt.month}/{dt.day}"


def title_line_count(draw, title, title_font, title_x):
    if not title:
        return 1
    max_width = CANVAS_WIDTH - RIGHT_MARGIN - title_x
    lines = wrap_text(draw, title, title_font, max_width)
    return max(1, len(lines))


def event_block_height(line_count):
    return line_count * TITLE_LINE_HEIGHT


def can_fit_event(y, line_count, content_bottom, row_spacing):
    return y + row_spacing + event_block_height(line_count) <= content_bottom


def draw_wrapped_title(draw, title_font, x, y, title, max_width):
    if not title:
        return 1
    lines = wrap_text(draw, title, title_font, max_width)
    for j, wline in enumerate(lines):
        draw.text(
            (x, y + j * TITLE_LINE_HEIGHT),
            wline,
            font=title_font,
            fill=(255, 255, 255),
        )
    return len(lines)


def draw_this_week_row(draw, font, title_font, y, day_name, time_str, title):
    draw.text((LEFT_MARGIN, y), day_name, font=font, fill=(255, 255, 255))
    draw.text((THIS_WEEK_TIME_X, y), time_str, font=font, fill=(255, 255, 255))
    title_max_width = CANVAS_WIDTH - RIGHT_MARGIN - THIS_WEEK_TITLE_X
    return draw_wrapped_title(
        draw, title_font, THIS_WEEK_TITLE_X, y, title, title_max_width
    )


def draw_upcoming_row(
    draw, font, title_font, y, day_abbrev, date_str, time_str, title
):
    draw.text((LEFT_MARGIN, y), day_abbrev, font=font, fill=(255, 255, 255))
    draw.text((UPCOMING_DATE_X, y), date_str, font=font, fill=(255, 255, 255))
    draw.text((UPCOMING_TIME_X, y), time_str, font=font, fill=(255, 255, 255))
    title_max_width = CANVAS_WIDTH - RIGHT_MARGIN - UPCOMING_TITLE_X
    return draw_wrapped_title(
        draw, title_font, UPCOMING_TITLE_X, y, title, title_max_width
    )


def section_heading_advance():
    return SECTION_FONT_SIZE + SECTION_HEADING_GAP_AFTER


def upcoming_section_overhead():
    return (
        INTER_SECTION_GAP
        + SECTION_DIVIDER_WIDTH
        + SECTION_DIVIDER_PADDING
        + section_heading_advance()
    )


def render_event_list(
    draw,
    font,
    title_font,
    list_start,
    events,
    content_bottom,
    row_spacing,
    draw_row,
    title_x,
    debug=0,
):
    for event_date, title in events:
        line_count = title_line_count(draw, title, title_font, title_x)
        if not can_fit_event(list_start, line_count, content_bottom, row_spacing):
            if debug:
                print(f"Skipping (no room): {title}")
            break
        list_start += row_spacing
        line_count = draw_row(
            draw, font, title_font, list_start, event_date, title
        )
        list_start += event_block_height(line_count)
    return list_start


def draw_section_heading(draw, font, y, label):
    draw.text((LEFT_MARGIN, y), label, font=font, fill=(255, 255, 255))
    return y + section_heading_advance()


def draw_this_week_event(draw, font, title_font, y, event_date, title):
    if event_date is None or not title:
        return 1
    day_abbrev = DAY_ABBREV[event_date.weekday()]
    time_str = format_time_compact(event_date)
    return draw_this_week_row(
        draw, font, title_font, y, day_abbrev, time_str, title
    )


def draw_upcoming_event(draw, font, title_font, y, event_date, title):
    if event_date is None or not title:
        return 1
    day_abbrev = DAY_ABBREV[event_date.weekday()]
    date_str = format_date_slash(event_date)
    time_str = format_time_compact(event_date)
    return draw_upcoming_row(
        draw, font, title_font, y, day_abbrev, date_str, time_str, title
    )


def fetch_events(api_url: str, debug: int = 0) -> list:
    request = Request(api_url)
    request.add_header("User-Agent", "cdr-mtn-tv")
    with urlopen(request) as f:
        events = json.loads(f.read().decode("utf-8"))
    if debug > 1:
        pp(events)
    return events


def event_row_for_editor(event_date, title) -> dict:
    """Format an event tuple for the web editor tables."""
    if event_date is None or not title:
        return {"day": "", "date": "", "time": "", "title": ""}
    return {
        "day": DAY_ABBREV[event_date.weekday()],
        "date": format_date_slash(event_date),
        "time": format_time_compact(event_date),
        "title": title,
    }


def streamed_events(events: list) -> list[dict]:
    """Events with 'streamed' in the title, formatted for the editor."""
    rows = []
    for event in events:
        if "tribe_events" not in event.get("post_type", ""):
            continue
        title = event.get("post_title", "")
        if "streamed" not in title.lower():
            continue
        date = event.get("_EventStartDate", [None])[0]
        if not date:
            continue
        event_date = datetime.fromisoformat(date)
        rows.append((event_date, event_row_for_editor(event_date, title)))
    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]


def editor_event_sections(events: list, debug: int = 0) -> dict:
    """Build This Week, Upcoming, and Streamed sections for the web editor."""
    this_week, upcoming = categorize_events(events, debug=debug)
    return {
        "this_week": [event_row_for_editor(d, t) for d, t in this_week],
        "upcoming": [event_row_for_editor(d, t) for d, t in upcoming],
        "streamed": streamed_events(events),
    }


def categorize_events(events: list, debug: int = 0) -> tuple[list, list]:
    today = datetime.now().date()
    all_future = []

    for event in events:
        if "tribe_events" not in event.get("post_type", ""):
            continue
        date = event.get("_EventStartDate", [None])[0]
        if not date:
            continue
        event_date = datetime.fromisoformat(date)
        event_day = event_date.date()
        title = event.get("post_title", "")
        print(f"{date} {title}")

        if event_day >= today:
            all_future.append((event_date, title))

        if debug:
            print(f"Event {title} on {date}")

    all_future.sort(key=lambda e: e[0])

    this_week_events = all_future[:THIS_WEEK_SLOT_COUNT]
    while len(this_week_events) < THIS_WEEK_SLOT_COUNT:
        this_week_events.append((None, ""))

    upcoming_events = all_future[THIS_WEEK_SLOT_COUNT:]
    return this_week_events, upcoming_events


def render_events(config: dict | None = None, debug: int = 0) -> Path:
    config = config or load_config()
    rotate_degrees = config.get("tv2", {}).get("rotate_degrees", -90)

    events = fetch_events(config["events_api_url"], debug=debug)
    this_week_events, upcoming_events = categorize_events(events, debug=debug)

    if debug:
        print("=======================")

    header_path = root_path(config["assets"]["events_header"])
    font_path = root_path(config["fonts"]["fallback"])
    output_path = root_path(config["output"]["tv2_events"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    calendar = Image.new(
        mode="RGB", size=(CANVAS_WIDTH, CANVAS_HEIGHT), color=(16, 16, 16)
    )
    with Image.open(header_path) as header:
        scale = CANVAS_WIDTH / header.width
        header_resized = header.resize(
            (CANVAS_WIDTH, int(header.height * scale)), Image.LANCZOS
        )
        calendar.paste(header_resized, (0, 0))
        content_top = header_resized.height + 30

    font = ImageFont.truetype(str(font_path), FONT_SIZE)
    title_font = ImageFont.truetype(str(font_path), TITLE_FONT_SIZE)
    section_font = ImageFont.truetype(str(font_path), SECTION_FONT_SIZE)
    draw = ImageDraw.Draw(calendar)

    content_bottom = CANVAS_HEIGHT - 40
    list_start = content_top
    row_spacing = EVENT_ROW_SPACING

    list_start = draw_section_heading(
        draw, section_font, list_start, "This Week"
    )

    list_start = render_event_list(
        draw,
        font,
        title_font,
        list_start,
        this_week_events,
        content_bottom,
        row_spacing,
        draw_this_week_event,
        THIS_WEEK_TITLE_X,
        debug=debug,
    )

    if list_start + upcoming_section_overhead() <= content_bottom:
        list_start += INTER_SECTION_GAP
        divider_y = list_start
        draw.rectangle(
            [
                (LEFT_MARGIN, divider_y),
                (
                    CANVAS_WIDTH - RIGHT_MARGIN,
                    divider_y + SECTION_DIVIDER_WIDTH,
                ),
            ],
            fill=(255, 255, 255),
        )
        list_start = divider_y + SECTION_DIVIDER_WIDTH + SECTION_DIVIDER_PADDING
        list_start = draw_section_heading(
            draw, section_font, list_start, "Upcoming"
        )

        render_event_list(
            draw,
            font,
            title_font,
            list_start,
            upcoming_events,
            content_bottom,
            row_spacing,
            draw_upcoming_event,
            UPCOMING_TITLE_X,
            debug=debug,
        )

    rotated = calendar.rotate(rotate_degrees, expand=True)
    rotated.save(output_path, quality=95)
    print(f"Saved events poster to {output_path} ({rotated.width}x{rotated.height})")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Render TV2 events poster")
    parser.add_argument(
        "-d", "--debug", action="count", default=0, help="Debug output"
    )
    args = parser.parse_args()
    render_events(debug=args.debug)


if __name__ == "__main__":
    main()
