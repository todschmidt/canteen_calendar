import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from pprint import pp
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(
    prog="export-events",
    description="Converts wordpress event export to a useable calendar",
)
parser.add_argument(
    "-d", "--debug", action="count", help="Enable debug output", default=False
)
args = parser.parse_args()

export_url = (
    "https://cedarmountaincanteen.com/"
    "wp-json/custom/v1/custom-event-exporter/"
)

SCRIPT_DIR = Path(__file__).resolve().parent
HEADER_PATH = SCRIPT_DIR / "header.png"

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
FONT_SIZE = 36
HEADER_FONT_SIZE = 60
SECTION_FONT_SIZE = 48
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
LINE_HEIGHT = FONT_SIZE + 15

# Target shrink for tightened column pairs (~15px at nominal gap sizes).
TIGHTEN_PX = 15
# Extra space after section headings (below "This Week" / "Upcoming" labels).
SECTION_HEADING_GAP_AFTER = LINE_HEIGHT - 15
# Vertical space between event rows.
_EVENT_ROW_SPACING_BASE = int(IMAGE_HEIGHT * 0.018) + 35
EVENT_ROW_SPACING = int(_EVENT_ROW_SPACING_BASE * 0.3)
# Gap between This Week and Upcoming (independent of halved event spacing).
INTER_SECTION_GAP = max(
    _EVENT_ROW_SPACING_BASE, _EVENT_ROW_SPACING_BASE * 2 - 50
)
SECTION_DIVIDER_WIDTH = 2
SECTION_DIVIDER_PADDING = 12
OUTPUT_IMAGE = "canteenmonthlyposter.jpg"
OUTPUT_IMAGE_ROTATED = "canteenmonthlyposter_rotated.jpg"


def scaled_gap(base_gap, tighten_px=TIGHTEN_PX):
    """Shrink a column gap by tighten_px using a scale factor."""
    return int(base_gap * (1 - tighten_px / base_gap))


def expanded_gap(base_gap, widen_px):
    """Widen a column gap by widen_px using a scale factor."""
    return int(base_gap * (1 + widen_px / base_gap))


# This week: day | time | title
_THIS_WEEK_GAP_DAY_TIME = 220
_THIS_WEEK_GAP_TIME_TITLE = scaled_gap(200)
THIS_WEEK_TIME_X = LEFT_MARGIN + _THIS_WEEK_GAP_DAY_TIME
THIS_WEEK_TITLE_X = THIS_WEEK_TIME_X + _THIS_WEEK_GAP_TIME_TITLE

# Upcoming: day | date | time | title
_UPCOMING_GAP_DAY_DATE = expanded_gap(90, 25)
_UPCOMING_GAP_DATE_TIME = scaled_gap(160)
_UPCOMING_GAP_TIME_TITLE = 190
UPCOMING_DATE_X = LEFT_MARGIN + _UPCOMING_GAP_DAY_DATE
UPCOMING_TIME_X = UPCOMING_DATE_X + _UPCOMING_GAP_DATE_TIME
UPCOMING_TITLE_X = UPCOMING_TIME_X + _UPCOMING_GAP_TIME_TITLE

DAY_ABBREV = {
    0: "Mon",
    1: "Tues",
    2: "Wed",
    3: "Thurs",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}


def wrap_text(draw, text, font, max_width):
    """Split text into lines that fit within max_width pixels."""
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


def monday_of_week(d):
    return d - timedelta(days=d.weekday())


def format_time_compact(dt):
    hour = dt.hour % 12 or 12
    suffix = "am" if dt.hour < 12 else "pm"
    if dt.minute == 0:
        return f"{hour}{suffix}"
    return f"{hour}:{dt.minute:02d}{suffix}"


def format_date_slash(dt):
    return f"{dt.month}/{dt.day}"


def title_line_count(draw, title, font, title_x):
    max_width = IMAGE_WIDTH - RIGHT_MARGIN - title_x
    lines = wrap_text(draw, title, font, max_width)
    return max(1, len(lines))


def event_block_height(line_count):
    return line_count * LINE_HEIGHT


def can_fit_event(y, line_count, content_bottom, row_spacing):
    """True if row spacing plus full wrapped block fits above content_bottom."""
    return y + row_spacing + event_block_height(line_count) <= content_bottom


def draw_wrapped_title(draw, font, x, y, title, max_width):
    lines = wrap_text(draw, title, font, max_width)
    for j, wline in enumerate(lines):
        draw.text((x, y + j * LINE_HEIGHT), wline, font=font, fill=(255, 255, 255))
    return len(lines)


def draw_this_week_row(draw, font, y, day_name, time_str, title):
    draw.text((LEFT_MARGIN, y), day_name, font=font, fill=(255, 255, 255))
    draw.text((THIS_WEEK_TIME_X, y), time_str, font=font, fill=(255, 255, 255))
    title_max_width = IMAGE_WIDTH - RIGHT_MARGIN - THIS_WEEK_TITLE_X
    return draw_wrapped_title(
        draw, font, THIS_WEEK_TITLE_X, y, title, title_max_width
    )


def draw_upcoming_row(draw, font, y, day_abbrev, date_str, time_str, title):
    draw.text((LEFT_MARGIN, y), day_abbrev, font=font, fill=(255, 255, 255))
    draw.text((UPCOMING_DATE_X, y), date_str, font=font, fill=(255, 255, 255))
    draw.text((UPCOMING_TIME_X, y), time_str, font=font, fill=(255, 255, 255))
    title_max_width = IMAGE_WIDTH - RIGHT_MARGIN - UPCOMING_TITLE_X
    return draw_wrapped_title(
        draw, font, UPCOMING_TITLE_X, y, title, title_max_width
    )


def section_heading_advance():
    return SECTION_FONT_SIZE + SECTION_HEADING_GAP_AFTER


def upcoming_section_overhead():
    """Vertical space for gap, divider, padding, and Upcoming heading."""
    return (
        INTER_SECTION_GAP
        + SECTION_DIVIDER_WIDTH
        + SECTION_DIVIDER_PADDING
        + section_heading_advance()
    )


def render_event_list(
    draw,
    font,
    list_start,
    events,
    content_bottom,
    row_spacing,
    draw_row,
    title_x,
):
    """Draw events; skip any that would clip (including wrapped titles)."""
    for event_date, title in events:
        line_count = title_line_count(draw, title, font, title_x)
        if not can_fit_event(list_start, line_count, content_bottom, row_spacing):
            if args.debug:
                print(f"Skipping (no room): {title}")
            break
        list_start += row_spacing
        line_count = draw_row(draw, font, list_start, event_date, title)
        list_start += event_block_height(line_count)
    return list_start


def draw_section_heading(draw, font, y, label):
    draw.text((LEFT_MARGIN, y), label, font=font, fill=(255, 255, 255))
    return y + section_heading_advance()


def draw_this_week_event(draw, font, y, event_date, title):
    day_name = event_date.strftime("%A")
    time_str = format_time_compact(event_date)
    return draw_this_week_row(draw, font, y, day_name, time_str, title)


def draw_upcoming_event(draw, font, y, event_date, title):
    day_abbrev = DAY_ABBREV[event_date.weekday()]
    date_str = format_date_slash(event_date)
    time_str = format_time_compact(event_date)
    return draw_upcoming_row(
        draw, font, y, day_abbrev, date_str, time_str, title
    )


def main():
    request = Request(export_url)
    request.add_header("User-Agent", "canteen-calendar")
    with urlopen(request) as f:
        events = json.loads(f.read().decode("utf-8"))

    # with open('./events-export.json', 'r') as f:
    #     events = json.loads(f.read())

    if args.debug > 1:
        pp(events)

    today = datetime.now().date()
    this_week_monday = monday_of_week(today)
    this_week_sunday = this_week_monday + timedelta(days=6)
    next_week_monday = this_week_monday + timedelta(days=7)

    this_week_events = []
    upcoming_events = []

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

        if this_week_monday <= event_day <= this_week_sunday:
            this_week_events.append((event_date, title))
        elif event_day >= next_week_monday:
            upcoming_events.append((event_date, title))

        if args.debug:
            print(f"Event {title} on {date}")

    this_week_events.sort(key=lambda e: e[0])
    upcoming_events.sort(key=lambda e: e[0])

    if args.debug:
        print("=======================")

    calendar = Image.new(
        mode="RGB", size=(IMAGE_WIDTH, IMAGE_HEIGHT), color=(16, 16, 16)
    )
    with Image.open(HEADER_PATH) as header:
        scale = IMAGE_WIDTH / header.width
        header_resized = header.resize(
            (IMAGE_WIDTH, int(header.height * scale)), Image.LANCZOS
        )
        calendar.paste(header_resized, (0, 0))
        content_top = header_resized.height + 30

    font = ImageFont.truetype(r"arialbd.ttf", FONT_SIZE)
    section_font = ImageFont.truetype(r"arialbd.ttf", SECTION_FONT_SIZE)
    draw = ImageDraw.Draw(calendar)

    content_bottom = IMAGE_HEIGHT - 40
    list_start = content_top
    row_spacing = EVENT_ROW_SPACING

    list_start = draw_section_heading(draw, section_font, list_start, "This Week")

    list_start = render_event_list(
        draw,
        font,
        list_start,
        this_week_events,
        content_bottom,
        row_spacing,
        draw_this_week_event,
        THIS_WEEK_TITLE_X,
    )

    if list_start + upcoming_section_overhead() <= content_bottom:
        list_start += INTER_SECTION_GAP
        divider_y = list_start
        draw.rectangle(
            [
                (LEFT_MARGIN, divider_y),
                (
                    IMAGE_WIDTH - RIGHT_MARGIN,
                    divider_y + SECTION_DIVIDER_WIDTH,
                ),
            ],
            fill=(255, 255, 255),
        )
        list_start = divider_y + SECTION_DIVIDER_WIDTH + SECTION_DIVIDER_PADDING
        list_start = draw_section_heading(
            draw, section_font, list_start, "Upcoming"
        )

        list_start = render_event_list(
            draw,
            font,
            list_start,
            upcoming_events,
            content_bottom,
            row_spacing,
            draw_upcoming_event,
            UPCOMING_TITLE_X,
        )

    calendar.show()
    calendar.save(OUTPUT_IMAGE)
    calendar.rotate(-90, expand=True).save(OUTPUT_IMAGE_ROTATED)


if __name__ == "__main__":
    main()
