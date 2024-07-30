import argparse
import re
from datetime import datetime
from pprint import pp
from PIL import Image, ImageOps, ImageDraw, ImageFont
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
                day = datetime.fromisoformat(date).strftime("%m%d")
                day_of_week = datetime.fromisoformat(date).strftime("%a")
                time = datetime.fromisoformat(date).strftime("%I:%M %p")
                # strip the leading zero from just the hour
                time_stripped = re.sub(r"^0+", " ", time)
                lines.append(
                    {day: f'{day_of_week} {time_stripped} {event.get("post_title")}'}
                )
                if args.debug:
                    print(f"Event {event.get('post_title')} on {date}")
    if args.debug:
        print("=======================")

    # Create the calendar image
    calendar = Image.new(mode="RGB", size=(1080, 1920), color=(64, 64, 64))
    with Image.open("canteenmonthlyposterheader.jpg") as header:
        calendar.paste(ImageOps.contain(header, (1080, int(1920 * 0.27))), (0, 0))
    with Image.open("canteenmonthlyposterfooter.jpg") as footer:
        calendar.paste(
            ImageOps.contain(footer, (1080, int(1920 * 0.27))), (0, int(1920 * 0.82))
        )

    font = ImageFont.truetype(r"arialbd.ttf", 24)
    header_font = ImageFont.truetype(r"arialbd.ttf", 40)
    text = ImageDraw.Draw(calendar)

    month = datetime.today().month

    # Add the events to the calendar
    list_start = int(1920 * 0.26)
    list_spacing = int(1920 * 0.016)
    for event in sorted(lines, key=lambda d: list(d.keys())):
        for key, value in event.items():
            if month < int(key[0:2]):
                month += 1
            list_start += list_spacing
            # break so we don't write past footer
            if list_start + list_spacing > int(1920 * 0.82):
                break
            # add month separator
            if month == int(key[0:2]):
                list_start += list_spacing * 0.05
                text.text(
                    (0, list_start),
                    f"{datetime(2024, month, 1).strftime('%B')} Events",
                    font=header_font,
                    fill=(255, 255, 255),
                )
                month += 1
                list_start += list_spacing * 1.8
            day = f"{key[len(key)-2:]}"
            day_of_week, event_time, event_name = value.split(" ", 2)
            if args.debug:
                print(f"{day} {day_of_week} {event_time} {event_name}")
            text.text(
                (0, list_start),
                f"  {day}  {day_of_week}",
                font=font,
                fill=(255, 255, 255),
            )
            text.text(
                (1080 * 0.10, list_start),
                f"{event_time} {event_name}",
                font=font,
                fill=(255, 255, 255),
            )

    # Show the calendar in an image viewer
    calendar.show()
    calendar.save("canteenmonthlyposter.jpg")


if __name__ == "__main__":
    main()