import argparse
import json
import boto3
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import quote
import xml.etree.ElementTree as ET
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import hashlib

# S3 user metadata key for cached duration (seconds). Set by audio-processor on upload;
# read by the RSS Lambda via head_object to avoid downloading each file.
S3_DURATION_METADATA_KEY = 'duration-seconds'

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.aac')


def _configure_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S',
        ))
        root.addHandler(handler)


def _remaining_ms(context):
    if context is None or not hasattr(context, 'get_remaining_time_in_millis'):
        return None
    return context.get_remaining_time_in_millis()


def _log_remaining(context, label):
    remaining = _remaining_ms(context)
    if remaining is not None:
        logger.info('%s — %dms remaining before Lambda timeout', label, remaining)
        if remaining < 5000:
            logger.warning(
                'Less than 5s remaining; function may time out before finishing'
            )


def _parse_run_options(event):
    """Extract debug/run options from Lambda event or manual invocation payload."""
    options = {
        'debug': os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes'),
        'skip_metadata': False,
        'dry_run': False,
        'limit': None,
    }
    if isinstance(event, dict):
        options['debug'] = options['debug'] or bool(event.get('debug'))
        options['skip_metadata'] = bool(event.get('skip_metadata'))
        options['dry_run'] = bool(event.get('dry_run'))
        if event.get('limit') is not None:
            options['limit'] = int(event['limit'])
    return options


def _list_bucket_objects(s3_client, bucket_name):
    """List all S3 objects, handling pagination."""
    objects = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name):
        objects.extend(page.get('Contents', []))
    return objects


def handler(event, context):
    """
    Lambda function to generate RSS feed for podcast episodes.

    Manual invocation payload (optional):
      {"debug": true}           — verbose timing logs
      {"skip_metadata": true}   — skip downloading files for duration (fast test)
      {"dry_run": true}         — build RSS but do not upload to S3
      {"limit": 3}              — process only the first N audio files
    """
    options = _parse_run_options(event or {})
    _configure_logging(options['debug'])
    run_start = time.monotonic()

    logger.info('RSS generator started')
    if options['debug']:
        logger.debug('Run options: %s', options)
        logger.debug('Event: %s', json.dumps(event or {}, default=str)[:500])
    _log_remaining(context, 'At start')

    s3_client = boto3.client('s3')

    # Get environment variables
    bucket_name = os.environ['BUCKET_NAME']
    podcast_title = os.environ['PODCAST_TITLE']
    podcast_description = os.environ['PODCAST_DESCRIPTION']
    podcast_author = os.environ['PODCAST_AUTHOR']
    podcast_email = os.environ['PODCAST_EMAIL']
    cloudfront_domain = os.environ['CLOUDFRONT_DOMAIN']
    domain_name = os.environ.get('DOMAIN_NAME', '')
    artwork_url = os.environ.get(
        'ARTWORK_URL',
        'https://cedarmountainnews.todschmidt.com/artwork.jpg'
    )
    podcast_category = os.environ.get('PODCAST_CATEGORY', 'News')
    podcast_category_subcategory = os.environ.get(
        'PODCAST_CATEGORY_SUBCATEGORY', 'Local'
    )

    # Determine the base URL for the podcast
    if domain_name:
        base_url = f"https://{domain_name}"
    else:
        base_url = f"https://{cloudfront_domain}"

    timing = {}

    try:
        list_start = time.monotonic()
        all_objects = _list_bucket_objects(s3_client, bucket_name)
        timing['list_bucket_s'] = time.monotonic() - list_start
        logger.info(
            'Listed %d objects from s3://%s in %.2fs',
            len(all_objects), bucket_name, timing['list_bucket_s'],
        )

        if not all_objects:
            logger.info('No objects found in bucket')
            return {
                'statusCode': 200,
                'body': json.dumps('No episodes found')
            }

        audio_objects = [
            obj for obj in all_objects
            if obj['Key'].lower().endswith(AUDIO_EXTENSIONS)
        ]
        logger.info('Found %d audio files', len(audio_objects))

        if options['limit'] is not None:
            audio_objects = audio_objects[:options['limit']]
            logger.info('Processing limited to %d files', len(audio_objects))

        if options['skip_metadata']:
            logger.warning(
                'skip_metadata enabled — durations will be 00:00:00'
            )

        metadata_total_s = 0.0
        metadata_sources = {'s3': 0, 'download': 0, 'skipped': 0, 'none': 0}
        audio_files = []
        for index, obj in enumerate(audio_objects, start=1):
            key = obj['Key']
            file_start = time.monotonic()
            _log_remaining(context, f'Before metadata for file {index}/{len(audio_objects)}')

            if options['skip_metadata']:
                duration = 0
                source = 'skipped'
            else:
                duration, source = get_episode_duration(
                    s3_client, bucket_name, key, debug=options['debug'],
                )

            metadata_sources[source] = metadata_sources.get(source, 0) + 1
            file_elapsed = time.monotonic() - file_start
            metadata_total_s += file_elapsed
            logger.info(
                'File %d/%d: %s (%.1f MB) duration=%ds via %s in %.2fs',
                index, len(audio_objects), key,
                obj['Size'] / (1024 * 1024), duration, source, file_elapsed,
            )

            parsed_date = extract_date_from_filename(key)

            if parsed_date is None:
                pub_date = obj['LastModified']
                episode_date = obj['LastModified'].date()
            else:
                now = datetime.now(timezone.utc)
                pub_date = parsed_date.replace(
                    hour=now.hour, minute=now.minute,
                    second=now.second, microsecond=now.microsecond,
                )
                episode_date = parsed_date.date()

            audio_files.append({
                'key': key,
                'last_modified': obj['LastModified'],
                'pub_date': pub_date,
                'episode_date': episode_date,
                'size': obj['Size'],
                'duration': duration,
            })

        timing['metadata_total_s'] = metadata_total_s
        timing['metadata_avg_s'] = (
            metadata_total_s / len(audio_objects) if audio_objects else 0
        )
        timing['metadata_sources'] = metadata_sources
        logger.info(
            'Metadata phase complete: %.2fs total, %.2fs avg per file '
            '(s3=%d, download=%d, skipped=%d, none=%d)',
            timing['metadata_total_s'], timing['metadata_avg_s'],
            metadata_sources.get('s3', 0),
            metadata_sources.get('download', 0),
            metadata_sources.get('skipped', 0),
            metadata_sources.get('none', 0),
        )
        _log_remaining(context, 'After metadata phase')

        audio_files.sort(key=lambda x: x['pub_date'], reverse=True)
        test_player_url = f"{base_url}/test-player.html"

        rss_start = time.monotonic()
        rss_content = generate_rss_feed(
            audio_files,
            base_url,
            podcast_title,
            podcast_description,
            podcast_author,
            podcast_email,
            artwork_url,
            podcast_category,
            podcast_category_subcategory,
            test_player_url
        )
        timing['generate_rss_s'] = time.monotonic() - rss_start
        logger.info('Generated RSS feed in %.2fs', timing['generate_rss_s'])

        if options['dry_run']:
            logger.warning('dry_run enabled — skipping S3 upload')
        else:
            upload_start = time.monotonic()
            s3_client.put_object(
                Bucket=bucket_name,
                Key='rss.xml',
                Body=rss_content.encode('utf-8'),
                ContentType='application/rss+xml',
                CacheControl='no-cache, no-store, must-revalidate',
            )
            timing['upload_rss_s'] = time.monotonic() - upload_start
            logger.info('Uploaded rss.xml in %.2fs', timing['upload_rss_s'])

        timing['total_s'] = time.monotonic() - run_start
        latest_episode = None
        if audio_files:
            latest = audio_files[0]
            latest_episode = {
                'file': latest['key'],
                'title': generate_episode_title(latest['key']),
                'pub_date': latest['pub_date'].strftime('%Y-%m-%d'),
            }

        summary = (
            f'RSS feed updated with {len(audio_files)} episodes in '
            f'{timing["total_s"]:.2f}s'
        )
        if latest_episode:
            summary += (
                f'; latest episode: {latest_episode["file"]} '
                f'({latest_episode["pub_date"]})'
            )
        logger.info(summary)
        if options['debug']:
            logger.info('Timing breakdown: %s', json.dumps(timing, indent=2))

        body = {
            'message': summary,
            'episodes': len(audio_files),
            'latest_episode': latest_episode,
            'timing': timing,
        }
        if options['dry_run']:
            body['dry_run'] = True

        return {
            'statusCode': 200,
            'body': json.dumps(body),
        }

    except Exception as e:
        elapsed = time.monotonic() - run_start
        logger.error(
            'Error generating RSS feed after %.2fs: %s',
            elapsed, e,
        )
        logger.error(traceback.format_exc())
        raise


def generate_rss_feed(audio_files, base_url, podcast_title,
                      podcast_description, podcast_author, podcast_email,
                      artwork_url, podcast_category,
                      podcast_category_subcategory, test_player_url):
    """
    Generate RSS 2.0 XML feed for podcast episodes
    """
    # Create RSS root element
    rss = ET.Element('rss')
    rss.set('version', '2.0')
    rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
    rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')

    # Create channel element
    channel = ET.SubElement(rss, 'channel')

    # Channel metadata
    ET.SubElement(channel, 'title').text = podcast_title
    ET.SubElement(channel, 'description').text = podcast_description
    ET.SubElement(channel, 'link').text = base_url
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'copyright').text = (
        f'Copyright {datetime.now(timezone.utc).year} {podcast_author}')
    ET.SubElement(channel, 'managingEditor').text = podcast_email
    ET.SubElement(channel, 'webMaster').text = podcast_email
    ET.SubElement(channel, 'lastBuildDate').text = (
        datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'))
    ET.SubElement(channel, 'generator').text = 'AWS Lambda RSS Generator'

    # iTunes specific channel tags
    ET.SubElement(channel, 'itunes:author').text = podcast_author
    ET.SubElement(channel, 'itunes:summary').text = podcast_description

    # itunes:owner must contain nested name and email
    owner = ET.SubElement(channel, 'itunes:owner')
    ET.SubElement(owner, 'itunes:name').text = podcast_author
    ET.SubElement(owner, 'itunes:email').text = podcast_email

    # itunes:image (required for Apple/Spotify)
    image = ET.SubElement(channel, 'itunes:image')
    image.set('href', artwork_url)

    ET.SubElement(channel, 'itunes:explicit').text = 'no'
    
    # itunes:type - episodic (standalone) or serial (sequential)
    ET.SubElement(channel, 'itunes:type').text = 'episodic'

    # itunes:category with nested subcategory
    # ElementTree automatically handles XML escaping
    category = ET.SubElement(channel, 'itunes:category')
    category.set('text', podcast_category.strip())
    
    # Add subcategory if provided
    if podcast_category_subcategory and podcast_category_subcategory.strip():
        subcategory = ET.SubElement(category, 'itunes:category')
        subcategory.set('text', podcast_category_subcategory.strip())

    # Add episodes
    total_episodes = len(audio_files)
    for i, audio_file in enumerate(audio_files):
        item = ET.SubElement(channel, 'item')

        # Generate episode title from filename
        episode_title = generate_episode_title(audio_file['key'])
        ET.SubElement(item, 'title').text = episode_title

        # Episode link to test player (RSS 2.0 spec: link should come early)
        encoded_filename = quote(audio_file['key'], safe='')
        episode_link = f"{test_player_url}?episode={encoded_filename}"
        ET.SubElement(item, 'link').text = episode_link

        # Generate episode description using parsed date from filename
        episode_description = generate_episode_description(
            audio_file['key'], audio_file['episode_date'])
        ET.SubElement(item, 'description').text = episode_description

        # Generate GUID (unique identifier) - permanent, never reused
        # Format: cedarmountainnews-YYYY-MM-DD[-suffix]
        # Use episode_date (parsed from filename) for consistency
        guid = generate_permanent_guid(audio_file['key'], audio_file['episode_date'])
        guid_elem = ET.SubElement(item, 'guid')
        guid_elem.text = guid
        guid_elem.set('isPermaLink', 'false')

        # Publication date (extracted from filename, with current time)
        pub_date = audio_file['pub_date'].strftime(
            '%a, %d %b %Y %H:%M:%S GMT')
        ET.SubElement(item, 'pubDate').text = pub_date

        # Enclosure (audio file) - URL encode filename properly
        # Files should have _v2 suffix for cache-busting (renamed manually)
        # Encode spaces and special characters (don't use safe='/')
        # Split path and encode each segment separately to preserve slashes
        path_parts = audio_file['key'].split('/')
        encoded_parts = [quote(part, safe='') for part in path_parts]
        encoded_key = '/'.join(encoded_parts)
        audio_url = f"{base_url}/{encoded_key}"
        enclosure = ET.SubElement(item, 'enclosure')
        enclosure.set('url', audio_url)
        enclosure.set('length', str(audio_file['size']))
        enclosure.set('type', get_mime_type(audio_file['key']))

        # iTunes specific item tags
        ET.SubElement(item, 'itunes:title').text = episode_title
        ET.SubElement(item, 'itunes:summary').text = episode_description
        ET.SubElement(item, 'itunes:author').text = podcast_author
        
        # itunes:duration - use real duration from audio file
        duration_str = format_duration(audio_file.get('duration', 0))
        ET.SubElement(item, 'itunes:duration').text = duration_str
        
        # itunes:episodeType - full, trailer, or bonus
        ET.SubElement(item, 'itunes:episodeType').text = 'full'
        
        # itunes:episode - episode number (oldest = 1, newest = total_episodes)
        # Episodes are sorted newest first, so reverse the numbering
        episode_number = total_episodes - i
        ET.SubElement(item, 'itunes:episode').text = str(episode_number)
        
        ET.SubElement(item, 'itunes:explicit').text = 'no'

    # Convert to string
    # ElementTree automatically handles XML escaping (e.g., & becomes &amp;)
    # No manual escaping needed - ElementTree handles it correctly
    rss_xml = ET.tostring(rss, encoding='unicode', xml_declaration=True)
    
    return rss_xml


_MONTH_NAME_TO_NUMBER = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}

# Any run of non-digits between date parts (handles mixed -, _, ., /, spaces, etc.)
_DATE_SEP = r'[^\d]+'
_MONTH_NAME_PATTERN = (
    r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|'
    r'Nov(?:ember)?|Dec(?:ember)?)'
)


def _month_name_to_number(name):
    return _MONTH_NAME_TO_NUMBER.get(str(name).strip().lower())


def _try_build_date(year, month, day):
    """Return a UTC datetime for valid calendar components, else None."""
    try:
        year = int(year)
        month = int(month)
        day = int(day)
    except (TypeError, ValueError):
        return None

    if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return None

    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_delimited_numeric_date(text, order):
    """
    Parse the last delimited numeric date in text.
    order: 'ymd' (2026-01-14), 'mdy' (01-14-2026), or 'dmy' (14-01-2026)
    """
    if order == 'ymd':
        pattern = (
            r'(\d{4})' + _DATE_SEP + r'(\d{1,2})' + _DATE_SEP + r'(\d{1,2})'
            r'(?!\d)'
        )
        groups = ('year', 'month', 'day')
    elif order == 'mdy':
        pattern = (
            r'(\d{1,2})' + _DATE_SEP + r'(\d{1,2})' + _DATE_SEP + r'(\d{4})'
            r'(?!\d)'
        )
        groups = ('month', 'day', 'year')
    elif order == 'dmy':
        pattern = (
            r'(\d{1,2})' + _DATE_SEP + r'(\d{1,2})' + _DATE_SEP + r'(\d{4})'
            r'(?!\d)'
        )
        groups = ('day', 'month', 'year')
    else:
        return None

    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    if not matches:
        return None

    match = matches[-1]
    parts = dict(zip(groups, match.groups()))
    return _try_build_date(parts['year'], parts['month'], parts['day'])


def _parse_compact_eight_digit_date(text):
    """Parse YYYYMMDD or MMDDYYYY compact dates (e.g. 20260114, 01142026)."""
    matches = list(re.finditer(r'(?<!\d)(\d{8})(?!\d)', text))
    if not matches:
        return None

    digits = matches[-1].group(1)
    yyyy, mm, dd = int(digits[0:4]), int(digits[4:6]), int(digits[6:8])

    parsed = _try_build_date(yyyy, mm, dd)
    if parsed:
        return parsed

    mm2, dd2, yyyy2 = int(digits[0:2]), int(digits[2:4]), int(digits[4:8])
    return _try_build_date(yyyy2, mm2, dd2)


def _parse_month_name_date(text):
    """Parse dates with month names, e.g. Jan-14-2026 or 14_January_2026."""
    month_first = (
        r'(?P<month>' + _MONTH_NAME_PATTERN + r')' + _DATE_SEP +
        r'(?P<day>\d{1,2})' + _DATE_SEP + r'(?P<year>\d{4})'
    )
    day_first = (
        r'(?P<day>\d{1,2})' + _DATE_SEP +
        r'(?P<month>' + _MONTH_NAME_PATTERN + r')' + _DATE_SEP +
        r'(?P<year>\d{4})'
    )

    for pattern in (month_first, day_first):
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        if not matches:
            continue
        match = matches[-1]
        month = _month_name_to_number(match.group('month'))
        if month is None:
            continue
        parsed = _try_build_date(
            match.group('year'),
            month,
            match.group('day'),
        )
        if parsed:
            return parsed
    return None


def _parse_datetime_formats(text):
    """Parse explicit datetime strings (common in ID3 tags and timestamps)."""
    cleaned = str(text).strip()
    if not cleaned:
        return None

    # Strip trailing timezone labels and Z suffix for strptime attempts.
    normalized = re.sub(r'\s*(Z|[+-]\d{2}:?\d{2})$', '', cleaned, flags=re.IGNORECASE)

    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%m.%d.%Y',
        '%m_%d_%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%d.%m.%Y',
        '%d_%m_%Y',
        '%Y%m%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
        '%Y',
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def parse_date_string(text):
    """
    Parse a date from arbitrary text using multiple strategies.
    Returns a UTC datetime or None.
    """
    if text is None:
        return None

    cleaned = str(text).strip()
    if not cleaned:
        return None

    parsers = (
        _parse_datetime_formats,
        lambda t: _parse_delimited_numeric_date(t, 'mdy'),
        lambda t: _parse_delimited_numeric_date(t, 'ymd'),
        lambda t: _parse_delimited_numeric_date(t, 'dmy'),
        _parse_compact_eight_digit_date,
        _parse_month_name_date,
    )

    for parser in parsers:
        parsed = parser(cleaned)
        if parsed is not None:
            return parsed

    return None


def extract_date_from_filename(filename):
    """
    Extract a publication date from a filename.

    Supports flexible separators (-, _, ., /, spaces, and mixed), compact
    formats (YYYYMMDD / MMDDYYYY), ISO order (YYYY-MM-DD), and month names.
    Uses the last valid match so title numbers do not override episode dates.
    """
    normalized = filename.replace('\\', '/')
    if '.' in normalized.rsplit('/', 1)[-1]:
        text = normalized.rsplit('.', 1)[0]
    else:
        text = normalized
    return parse_date_string(text)


def parse_id3_date(date_str):
    """
    Parse various date formats from ID3 tags.
    Returns a UTC datetime or None if parsing fails.
    """
    parsed = parse_date_string(date_str)
    if parsed is not None:
        return parsed

    # Last resort: leading four-digit year only.
    try:
        year = int(str(date_str).strip()[:4])
        if 1900 <= year <= 2100:
            return datetime(year, 1, 1, tzinfo=timezone.utc)
    except (ValueError, IndexError):
        pass

    return None



def generate_permanent_guid(filename, episode_date):
    """
    Generate a permanent, unique GUID for an episode.
    Format: cedarmountainnews-YYYY-MM-DD[-suffix]
    The suffix is added only if needed to ensure uniqueness.
    GUIDs are permanent and never reused or reassigned.
    episode_date can be a date or datetime object.
    """
    # Base GUID format: cedarmountainnews-YYYY-MM-DD
    # Handle both date and datetime objects
    if hasattr(episode_date, 'strftime'):
        date_str = episode_date.strftime('%Y-%m-%d')
    else:
        # Fallback: convert to string and extract date part
        date_str = str(episode_date)[:10]  # YYYY-MM-DD format
    base_guid = f"cedarmountainnews-{date_str}"
    
    # Create a deterministic hash from filename to ensure uniqueness
    # if multiple episodes exist on the same day
    filename_hash = hashlib.md5(filename.encode('utf-8')).hexdigest()[:8]
    
    # Use hash suffix to ensure uniqueness (even if same date)
    # This ensures GUID is permanent and tied to the specific file
    guid = f"{base_guid}-{filename_hash}"
    
    return guid


def generate_episode_title(filename):
    """
    Generate a human-readable title from the filename
    """
    # Remove file extension and replace underscores/hyphens with spaces
    title = os.path.splitext(filename)[0]
    title = title.replace('_', ' ').replace('-', ' ')
    # Capitalize words
    title = ' '.join(word.capitalize() for word in title.split())
    return title


def generate_episode_description(filename, episode_date):
    """
    Generate a description for the episode using the parsed date from filename
    episode_date can be a date object or datetime object
    """
    # Format date nicely: "December 17, 2025"
    if hasattr(episode_date, 'strftime'):
        date_str = episode_date.strftime('%B %d, %Y')
    else:
        # Fallback if it's already a string or other format
        date_str = str(episode_date)
    return (
        f"Episode from {date_str}. "
        f"Join us for the latest community news and updates from "
        f"Cedar Mountain, North Carolina."
    )


def get_mime_type(filename):
    """
    Get MIME type based on file extension
    """
    extension = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/wav',
        '.aac': 'audio/aac'
    }
    return mime_types.get(extension, 'audio/mpeg')


def get_duration_from_s3_metadata(s3_client, bucket_name, key, debug=False):
    """Read cached duration from S3 object metadata (head_object, no download)."""
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=key)
        raw = response.get('Metadata', {}).get(S3_DURATION_METADATA_KEY)
        if raw is None:
            return None
        duration = int(raw)
        if debug:
            logger.debug(
                'Duration %ds for %s from S3 metadata (%s)',
                duration, key, S3_DURATION_METADATA_KEY,
            )
        return duration
    except (ValueError, TypeError) as e:
        logger.warning(
            'Invalid %s metadata on %s: %s',
            S3_DURATION_METADATA_KEY, key, e,
        )
        return None
    except Exception as e:
        logger.debug('Could not read S3 metadata for %s: %s', key, e)
        return None


def backfill_s3_duration_metadata(s3_client, bucket_name, key, duration):
    """Store duration on the S3 object so future RSS runs skip the download."""
    try:
        head = s3_client.head_object(Bucket=bucket_name, Key=key)
        metadata = dict(head.get('Metadata', {}))
        metadata[S3_DURATION_METADATA_KEY] = str(duration)
        copy_kwargs = {
            'Bucket': bucket_name,
            'Key': key,
            'CopySource': {'Bucket': bucket_name, 'Key': key},
            'Metadata': metadata,
            'MetadataDirective': 'REPLACE',
            'ContentType': head.get('ContentType', get_mime_type(key)),
        }
        if head.get('CacheControl'):
            copy_kwargs['CacheControl'] = head['CacheControl']
        s3_client.copy_object(**copy_kwargs)
        logger.info('Backfilled %s=%d on %s', S3_DURATION_METADATA_KEY, duration, key)
        return True
    except Exception as e:
        logger.warning('Failed to backfill metadata for %s: %s', key, e)
        return False


def get_episode_duration(s3_client, bucket_name, key, debug=False, backfill=True):
    """
    Get episode duration, preferring S3 object metadata over downloading the file.
    Returns (duration_seconds, source) where source is 's3', 'download', or 'none'.
    """
    duration = get_duration_from_s3_metadata(
        s3_client, bucket_name, key, debug=debug,
    )
    if duration is not None:
        return duration, 's3'

    logger.info(
        'No %s on %s — downloading file for duration',
        S3_DURATION_METADATA_KEY, key,
    )
    duration, _ = get_audio_metadata(s3_client, bucket_name, key, debug=debug)
    if duration > 0:
        if backfill:
            backfill_s3_duration_metadata(s3_client, bucket_name, key, duration)
        return duration, 'download'
    return 0, 'none'


def get_audio_metadata(s3_client, bucket_name, key, debug=False):
    """
    Get duration and publication date from audio file metadata
    Returns tuple: (duration in seconds, publication datetime or None)
    """
    temp_file = None
    try:
        temp_file = f'/tmp/{os.path.basename(key)}'
        download_start = time.monotonic()
        s3_client.download_file(bucket_name, key, temp_file)
        download_s = time.monotonic() - download_start
        if debug:
            logger.debug('Downloaded %s in %.2fs', key, download_s)

        parse_start = time.monotonic()
        audio_file = File(temp_file)
        if audio_file is None:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return (0, None)
        
        duration = int(audio_file.info.length) if hasattr(
            audio_file, 'info') and hasattr(audio_file.info, 'length') else 0
        
        # Try to extract publication date from ID3 tags
        pub_date = None
        
        # For MP3 files, check ID3 tags
        if isinstance(audio_file, MP3):
            try:
                id3 = audio_file.tags
                if id3 is not None:
                    # Try TDRC (Recording time) - ID3v2.4
                    if 'TDRC' in id3:
                        tdrc = id3['TDRC']
                        # Handle both string and TimeStampTextFrame objects
                        if isinstance(tdrc, list) and len(tdrc) > 0:
                            tdrc_value = tdrc[0]
                            if isinstance(tdrc_value, str):
                                pub_date = parse_id3_date(tdrc_value)
                            elif (hasattr(tdrc_value, 'text') and
                                  tdrc_value.text):
                                pub_date = parse_id3_date(tdrc_value.text[0])
                            elif hasattr(tdrc_value, '__str__'):
                                pub_date = parse_id3_date(str(tdrc_value))
                        elif isinstance(tdrc, str):
                            pub_date = parse_id3_date(tdrc)
                    
                    # Fall back to TYER + TDAT (ID3v2.3)
                    if pub_date is None:
                        year = None
                        date = None
                        if 'TYER' in id3:
                            year = str(id3['TYER'][0])
                        if 'TDAT' in id3:
                            date = str(id3['TDAT'][0])
                        if year and date:
                            # TDAT format: DDMM
                            if len(date) == 4:
                                day = date[:2]
                                month = date[2:]
                                date_str = f"{year}-{month}-{day}"
                                pub_date = parse_id3_date(date_str)
                    
                    # Try TXXX custom date field
                    if pub_date is None:
                        for frame in id3.getall('TXXX'):
                            if frame.desc and 'date' in frame.desc.lower():
                                pub_date = parse_id3_date(frame.text[0])
                                break
            except Exception as e:
                logger.debug('Error reading ID3 tags for %s: %s', key, e)
        
        # For MP4/M4A files, check metadata
        elif isinstance(audio_file, MP4):
            try:
                if audio_file.tags is not None:
                    # Check for date tag
                    if '\xa9day' in audio_file.tags:
                        date_str = str(audio_file.tags['\xa9day'][0])
                        pub_date = parse_id3_date(date_str)
            except Exception as e:
                logger.debug('Error reading MP4 tags for %s: %s', key, e)
        
        parse_s = time.monotonic() - parse_start
        if debug:
            logger.debug(
                'Parsed metadata for %s in %.2fs (duration=%ds)',
                key, parse_s, duration,
            )

        os.remove(temp_file)
        return (duration, pub_date)

    except Exception as e:
        logger.warning('Error getting metadata for %s: %s', key, e)
        # Clean up temp file if it exists
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        return (0, None)


def format_duration(seconds):
    """
    Format duration in seconds to HH:MM:SS or MM:SS format
    """
    if seconds == 0:
        return '00:00:00'
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d}"
    else:
        return f"{int(minutes):02d}:{int(secs):02d}"


class _LocalLambdaContext:
    """Minimal Lambda context for local runs."""

    def __init__(self, timeout_seconds=30):
        self._start = time.monotonic()
        self._timeout_ms = timeout_seconds * 1000
        self.function_name = 'local-rss-generator'
        self.memory_limit_in_mb = 128

    def get_remaining_time_in_millis(self):
        elapsed_ms = (time.monotonic() - self._start) * 1000
        return max(0, int(self._timeout_ms - elapsed_ms))


def _load_env_from_terraform():
    """Populate env vars from terraform outputs and tfvars for local runs."""
    import subprocess

    module_dir = os.path.dirname(os.path.abspath(__file__))
    tfvars_path = os.path.join(module_dir, 'terraform.tfvars')

    if os.path.exists(tfvars_path):
        with open(tfvars_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == 'domain_name' and value:
                    subdomain = 'cedarmountainnews'
                    with open(tfvars_path, encoding='utf-8') as tfvars:
                        for sub_line in tfvars:
                            if sub_line.strip().startswith('subdomain'):
                                subdomain = sub_line.split('=')[1].strip().strip('"').strip("'")
                                break
                    os.environ.setdefault('DOMAIN_NAME', f'{subdomain}.{value}')
                elif key == 'podcast_title':
                    os.environ.setdefault('PODCAST_TITLE', value)
                elif key == 'podcast_description':
                    os.environ.setdefault('PODCAST_DESCRIPTION', value)
                elif key == 'podcast_author':
                    os.environ.setdefault('PODCAST_AUTHOR', value)
                elif key == 'podcast_email':
                    os.environ.setdefault('PODCAST_EMAIL', value)
                elif key == 'artwork_url':
                    os.environ.setdefault('ARTWORK_URL', value)
                elif key == 'podcast_category':
                    os.environ.setdefault('PODCAST_CATEGORY', value)
                elif key == 'podcast_category_subcategory':
                    os.environ.setdefault('PODCAST_CATEGORY_SUBCATEGORY', value)

    def tf_output(name):
        result = subprocess.run(
            ['terraform', 'output', '-raw', name],
            cwd=module_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    bucket = tf_output('s3_bucket_name')
    cloudfront = tf_output('cloudfront_domain_name')
    if bucket:
        os.environ.setdefault('BUCKET_NAME', bucket)
    if cloudfront:
        os.environ.setdefault('CLOUDFRONT_DOMAIN', cloudfront)


def _missing_env_vars():
    required = [
        'BUCKET_NAME', 'PODCAST_TITLE', 'PODCAST_DESCRIPTION',
        'PODCAST_AUTHOR', 'PODCAST_EMAIL', 'CLOUDFRONT_DOMAIN',
    ]
    return [name for name in required if not os.environ.get(name)]


def main():
    parser = argparse.ArgumentParser(
        description='Run the podcast RSS generator locally or inspect timing.',
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Enable verbose timing logs',
    )
    parser.add_argument(
        '--skip-metadata', action='store_true',
        help='Skip downloading audio files (fast; durations will be 00:00:00)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Build RSS but do not upload to S3',
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Process only the first N audio files',
    )
    parser.add_argument(
        '--timeout', type=int, default=30,
        help='Simulated Lambda timeout in seconds (default: 30)',
    )
    parser.add_argument(
        '--from-terraform', action='store_true',
        help='Load BUCKET_NAME and CLOUDFRONT_DOMAIN from terraform output',
    )
    args = parser.parse_args()

    if args.from_terraform:
        _load_env_from_terraform()

    missing = _missing_env_vars()
    if missing:
        parser.error(
            'Missing environment variables: '
            + ', '.join(missing)
            + '. Use --from-terraform or set them manually.'
        )

    event = {
        'debug': args.debug,
        'skip_metadata': args.skip_metadata,
        'dry_run': args.dry_run,
    }
    if args.limit is not None:
        event['limit'] = args.limit

    context = _LocalLambdaContext(timeout_seconds=args.timeout)
    result = handler(event, context)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

