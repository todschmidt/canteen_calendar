import os
import re
import sys
import io
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from PIL import Image
from lxml import html


EVENTS_URL = "https://www.cedarmountainoutpost.com/events"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "other_events.txt")


def fetch_events_page(url: str) -> str:
    headers = {"User-Agent": "canteen-calendar/1.0"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def find_poster_image_url(page_html: str, base_url: str) -> str:
    tree = html.fromstring(page_html)
    # Heuristics: look for img elements that likely contain the month poster
    candidates = tree.xpath(
        (
            "//img[contains(@src, 'October') or "
            "contains(@src, 'CMO-SummerSeries') or "
            "contains(@alt, 'Event') or contains(@class, 'wp-image')]/@src"
        )
    )
    if not candidates:
        # fallback to any image on the page
        candidates = tree.xpath('//img/@src')
    # Prefer larger images and png/jpg
    candidates = [
        c
        for c in candidates
        if any(ext in c.lower() for ext in [".png", ".jpg", ".jpeg", ".webp"])
    ]
    # Simple heuristic: pick the longest URL (often the asset with hashed name)
    if not candidates:
        raise RuntimeError("No image candidates found on events page")
    candidates.sort(key=lambda u: len(u), reverse=True)
    return urljoin(base_url, candidates[0])


def download_image(url: str) -> Image.Image:
    headers = {"User-Agent": "canteen-calendar/1.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def ocr_image_locally(image: Image.Image) -> str:
    # Use simple Tesseract-free heuristic OCR replacement is not present.
    # We will call OCR.Space free API if env OCR_SPACE_KEY is provided.
    api_key = os.environ.get("OCR_SPACE_KEY")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    files = {"file": ("poster.png", buf, "image/png")}
    data = {
        "apikey": api_key or "helloworld",
        "language": "eng",
        "OCREngine": 2,
    }
    resp = requests.post(
        "https://api.ocr.space/parse/image",
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("ParsedResults"):
        raise RuntimeError(f"OCR failed: {payload}")
    text = "\n".join(p.get("ParsedText", "") for p in payload["ParsedResults"])
    return text


def extract_events(text: str) -> list[tuple[datetime, str]]:
    # Parse lines like:
    #   Sun 10/26
    #   4–6 pm
    #   Live Music – Nikki Talley & Jason Sharp
    # and combine into a single event with a proper time range and title.
    lines = [
        line_text.strip()
        for line_text in text.splitlines()
        if line_text.strip()
    ]
    events: list[tuple[datetime, str]] = []
    # Month mapping
    months = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    # regexes for date and time
    time_re = re.compile(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)",
        re.I,
    )
    # time ranges like 4–6 pm or 4-6pm
    time_range_re = re.compile(
        r"(\d{1,2})\s*[\-\u2013]\s*(\d{1,2})\s*(am|pm)",
        re.I,
    )
    md_re = re.compile(
        r"(?P<mon>\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
        r"[a-z]*\b)\s*[-/.,]*\s*(?P<day>\d{1,2})",
        re.I,
    )
    md2_re = re.compile(
        r"(?P<mon>\d{1,2})\s*[-/.,]\s*(?P<day>\d{1,2})"
    )
    # day-of-week is not strictly required here; skipping explicit parse

    today = datetime.now()
    current_year = today.year

    i = 0
    while i < len(lines):
        line = lines[i]
        # find month/day on this line
        m = md_re.search(line) or md2_re.search(line)
        if not m:
            i += 1
            continue
        # parse month/day
        mon_raw = m.group("mon")
        if mon_raw.isdigit():
            mon = int(mon_raw)
        else:
            mon = months.get(mon_raw.lower()[:3])
        day = int(m.group("day"))

        # Build a block from following lines until the next date.
        # Allow blank lines; cap the lookahead length to avoid runaway.
        block_lines = []
        j = i + 1
        while j < len(lines) and len(block_lines) < 8:
            nxt = lines[j]
            if md_re.search(nxt) or md2_re.search(nxt):
                break
            block_lines.append(nxt)
            j += 1

        # From block_lines, extract time range if present; else single time
        joined_block = " ".join(block_lines)
        tr = time_range_re.search(joined_block)
        tm = None if tr else time_re.search(joined_block)

        # Determine display time string and start time for datetime
        start_hour = 12
        start_minute = 0
        time_label = None
        if tr:
            start_hour = int(tr.group(1))
            ampm = tr.group(3).lower()
            time_label = f"{tr.group(1)}–{tr.group(2)} {ampm}"
        elif tm:
            start_hour = int(tm.group(1))
            start_minute = int(tm.group(2) or 0)
            ampm = (tm.group(3) or "").lower().replace(".", "")
            time_label = f"{start_hour}:{start_minute:02d} {ampm}".replace(
                ":00", ""
            )
        else:
            ampm = None

        if ampm and "p" in ampm and start_hour != 12:
            start_hour += 12
        if ampm and "a" in ampm and start_hour == 12:
            start_hour = 0

        event_dt = datetime(current_year, mon, day, start_hour, start_minute)

        # Title text is the block without the time-only line(s)
        title_candidates = []
        for bl in block_lines:
            if time_range_re.search(bl) or time_re.search(bl):
                continue
            if bl.strip():
                title_candidates.append(bl)
        raw_title = " ".join(title_candidates).strip(" -:\u2013\u2014")
        raw_title = re.sub(r"\s{2,}", " ", raw_title)
        if not raw_title:
            # skip events that did not yield a title
            i = max(j, i + 1)
            continue
        display_title = raw_title if not time_label else f"{time_label}: {raw_title}"

        events.append((event_dt, display_title))
        i = max(j, i + 1)

    return events


def filter_next_7_days(
    events: list[tuple[datetime, str]],
) -> list[tuple[datetime, str]]:
    start = datetime.now()
    end = start + timedelta(days=7)
    return [(dt, t) for dt, t in events if start <= dt <= end]


def update_other_events_file(events: list[tuple[datetime, str]]):
    # Preserve existing header and format
    if not os.path.exists(OUTPUT_FILE):
        existing = "### Cedar Mountain Outpost\n\n"
    else:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = f.read()

    lines = existing.rstrip().splitlines()
    # Ensure header exists
    if not lines or not lines[0].startswith("### Cedar Mountain Outpost"):
        lines = ["### Cedar Mountain Outpost", ""] + lines

    # Regenerate only the Outpost section (from header to next header or EOF)
    header_idx = None
    for idx, ln in enumerate(lines):
        if ln.strip().lower().startswith("### cedar mountain outpost"):
            header_idx = idx
            break
    if header_idx is None:
        lines = ["### Cedar Mountain Outpost", ""] + lines
        header_idx = 0

    # find end of section
    end_idx = len(lines)
    for idx in range(header_idx + 1, len(lines)):
        if lines[idx].startswith("### ") and idx > header_idx + 1:
            end_idx = idx
            break

    # Keep header and one blank line, then write fresh items
    new_lines = lines[: header_idx + 2]

    # Deduplicate by date and title
    seen = set()
    for dt, title in sorted(events, key=lambda x: x[0]):
        key = (dt.date(), title)
        if key in seen:
            continue
        seen.add(key)
        # Show as "- Sun 10/26, 4–6 pm: Title" if title begins with a time
        # We attempt to split leading time if present
        m = re.match(
            r"^(\d{1,2})(?:[:](\d{2}))?\s*(am|pm)[:]\s*(.+)",
            title,
            re.I,
        )
        if m:
            hr = int(m.group(1))
            mn = int(m.group(2) or 0)
            ap = m.group(3).lower()
            rest = m.group(4)
            time_str = f"{hr}:{mn:02d} {ap}".replace(":00", "")
            day_str = dt.strftime("%a %m/%d").replace(" 0", " ")
            new_lines.append(f"- {day_str}, {time_str}: {rest}")
        else:
            # If title contains a range at the start like "4–6 pm: Name"
            m2 = re.match(
                r"^(\d{1,2})[\-\u2013](\d{1,2})\s*(am|pm):\s*(.+)",
                title,
                re.I,
            )
            if m2:
                time_str = f"{m2.group(1)}–{m2.group(2)} {m2.group(3).lower()}"
                day_str = dt.strftime("%a %m/%d").replace(" 0", " ")
                new_lines.append(f"- {day_str}, {time_str}: {m2.group(4)}")
            else:
                day_str = dt.strftime("%a %m/%d %I:%M %p").replace(" 0", " ")
                new_lines.append(f"- {day_str} {title}")

    # Append the remainder after the section
    new_lines.extend(lines[end_idx:])
    lines = new_lines

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")


def main():
    page = fetch_events_page(EVENTS_URL)
    img_url = find_poster_image_url(page, EVENTS_URL)
    image = download_image(img_url)
    text = ocr_image_locally(image)
    events = extract_events(text)
    next_week = filter_next_7_days(events)
    update_other_events_file(next_week)
    message = (
        f"Updated {OUTPUT_FILE} with {len(next_week)} events from {img_url}"
    )
    print(message)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

