import argparse
import re
from datetime import datetime
from pprint import pp
from PIL import Image, ImageDraw, ImageFont
from urllib.request import Request, urlopen
import json

parser = argparse.ArgumentParser(
    prog="export-events",
    description="Converts wordpress event export " "to a useable calendar",
)
parser.add_argument(
    "-d", "--debug", action="count", help="Enable debug output", default=False
)
args = parser.parse_args()

export_url = 'https://cedarmountaincanteen.com/' \
            'wp-json/custom/v1/custom-event-exporter/'

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
FONT_SIZE = 36
HEADER_FONT_SIZE = 60
EVENT_TEXT_X = int(IMAGE_WIDTH * 0.15)
RIGHT_MARGIN = 20


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


def main():
    # Works but requires manual export
    # events = wpparser.parse("./export-events.xml")
    request = Request(export_url)

    # Testing locally
    # request = Request(
    #   'http://localhost:10004/wp-json/custom/v1/custom-event-exporter/')

    request.add_header("User-Agent", "canteen-calendar")
    with urlopen(request) as f:
        events = json.loads(f.read().decode("utf-8"))

    # curl #EXPORT_URL > events-export.json
    # Saves the file to avoid all the api calls
    # with open('./events-export.json', 'r') as f:
    #    events = json.loads(f.read())

    if args.debug > 1:
        pp(events)

    lines = []

    for event in events:
        if "tribe_events" in event.get("post_type"):
            date = event.get("_EventStartDate")[0]
            print(f"{date} {event.get('post_title')}")
            if date and datetime.fromisoformat(date) > datetime.today():
                event_date = datetime.fromisoformat(date)
                # Use YYYYMMDD format to preserve year for sorting
                day = event_date.strftime("%Y%m%d")
                day_of_week = event_date.strftime("%a")
                time = event_date.strftime("%I:%M %p")
                # strip the leading zero from just the hour
                time_stripped = re.sub(r"^0+", " ", time)
                event_title = event.get("post_title")
                lines.append(
                    {day: f'{day_of_week} {time_stripped} {event_title}'}
                )
                if args.debug:
                    print(f"Event {event.get('post_title')} on {date}")
    if args.debug:
        print("=======================")

    # Create the calendar image
    calendar = Image.new(
        mode="RGB", size=(IMAGE_WIDTH, IMAGE_HEIGHT), color=(64, 64, 64))
    with Image.open("canteenmonthlyposterheader.jpg") as header:
        scale = IMAGE_WIDTH / header.width
        header_resized = header.resize(
            (IMAGE_WIDTH, int(header.height * scale)), Image.LANCZOS)
        calendar.paste(header_resized, (0, 0))
    with Image.open("canteenmonthlyposterfooter.jpg") as footer:
        scale = IMAGE_WIDTH / footer.width
        footer_resized = footer.resize(
            (IMAGE_WIDTH, int(footer.height * scale)), Image.LANCZOS)
        footer_top = IMAGE_HEIGHT - footer_resized.height
        calendar.paste(footer_resized, (0, footer_top))

    font = ImageFont.truetype(r"arialbd.ttf", FONT_SIZE)
    header_font = ImageFont.truetype(r"arialbd.ttf", HEADER_FONT_SIZE)
    draw = ImageDraw.Draw(calendar)

    last_month = None
    last_year = None

    list_start = int(IMAGE_HEIGHT * 0.257)
    list_spacing = int(IMAGE_HEIGHT * 0.032)
    line_height = FONT_SIZE + 10

    for event in sorted(lines, key=lambda d: list(d.keys())):
        for key, value in event.items():
            event_year = int(key[0:4])
            event_month = int(key[4:6])
            event_day = int(key[6:8])

            list_start += list_spacing
            if list_start + list_spacing > footer_top:
                break

            month_changed = (
                last_month is None or
                event_month != last_month or
                event_year != last_year
            )
            if month_changed:
                if list_start + (list_spacing * 2) > footer_top:
                    break
                list_start += list_spacing * 0.04
                month_name = datetime(
                    event_year, event_month, 1
                ).strftime('%B %Y')
                draw.text(
                    (0, list_start),
                    f"{month_name} Events",
                    font=header_font,
                    fill=(255, 255, 255),
                )
                list_start += list_spacing * 1.8
                last_month = event_month
                last_year = event_year

            if list_start + list_spacing > footer_top:
                break
            day = f"{event_day}"
            day_of_week, event_time, event_name = value.split(" ", 2)
            if args.debug:
                print(f"{day} {day_of_week} {event_time} {event_name}")
            draw.text(
                (0, list_start),
                f"  {day}  {day_of_week}",
                font=font,
                fill=(255, 255, 255),
            )

            event_text = f"{event_time} {event_name}"
            time_match = re.match(
                r'(\s*\d{1,2}:\d{2}\s*[AP]M)\s+', event_text, re.IGNORECASE)
            if time_match:
                time_part = time_match.group(1)
                name_part = event_text[time_match.end():]
                time_width = draw.textlength(time_part + " ", font=font)
            else:
                time_part = ""
                name_part = event_text
                time_width = 0

            name_x = EVENT_TEXT_X + time_width
            name_max_width = IMAGE_WIDTH - RIGHT_MARGIN - name_x

            draw.text(
                (EVENT_TEXT_X, list_start),
                time_part,
                font=font,
                fill=(255, 255, 255),
            )

            wrapped_lines = wrap_text(draw, name_part, font, name_max_width)
            for j, wline in enumerate(wrapped_lines):
                y = list_start + j * line_height
                if y + line_height > footer_top:
                    break
                draw.text(
                    (name_x, y),
                    wline,
                    font=font,
                    fill=(255, 255, 255),
                )
            if len(wrapped_lines) > 1:
                list_start += (len(wrapped_lines) - 1) * line_height

    calendar.show()
    calendar.save("canteenmonthlyposter.jpg")


if __name__ == "__main__":
    main()
