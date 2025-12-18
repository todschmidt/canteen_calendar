import json
import boto3
import os
import re
from datetime import datetime
from urllib.parse import quote
import xml.etree.ElementTree as ET
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
import hashlib


def handler(event, context):
    """
    Lambda function to generate RSS feed for podcast episodes
    """
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

    try:
        # List all objects in the bucket
        response = s3_client.list_objects_v2(Bucket=bucket_name)

        if 'Contents' not in response:
            print("No objects found in bucket")
            return {
                'statusCode': 200,
                'body': json.dumps('No episodes found')
            }

        # Filter for audio files and get metadata
        audio_files = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.lower().endswith(('.mp3', '.m4a', '.wav', '.aac')):
                # Get duration from audio file metadata
                duration, _ = get_audio_metadata(s3_client, bucket_name, key)
                
                # Extract publication date from filename (format: MM_DD_YYYY or MM-DD-YYYY)
                # Store the parsed date (date only, no time) for description
                parsed_date = extract_date_from_filename(key)
                
                if parsed_date is None:
                    # Fall back to S3 upload date if no date found in filename
                    pub_date = obj['LastModified']
                    episode_date = obj['LastModified'].date()
                else:
                    # Use parsed date with current time when lambda runs
                    now = datetime.now()
                    pub_date = parsed_date.replace(hour=now.hour, minute=now.minute, 
                                                  second=now.second, microsecond=now.microsecond)
                    episode_date = parsed_date.date()

                audio_files.append({
                    'key': key,
                    'last_modified': obj['LastModified'],
                    'pub_date': pub_date,  # Full datetime for pubDate
                    'episode_date': episode_date,  # Date only for description
                    'size': obj['Size'],
                    'duration': duration
                })

        # Sort by publication date (newest first)
        audio_files.sort(key=lambda x: x['pub_date'], reverse=True)

        # Construct test player URL
        test_player_url = f"{base_url}/test-player.html"

        # Generate RSS feed
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

        # Upload RSS feed to S3
        # S3 automatically sets Content-Length header from Body size
        # Set Cache-Control to no-cache to prevent caching
        s3_client.put_object(
            Bucket=bucket_name,
            Key='rss.xml',
            Body=rss_content.encode('utf-8'),
            ContentType='application/rss+xml',
            CacheControl='no-cache, no-store, must-revalidate'  # Disable caching
        )

        print(f"RSS feed generated successfully with "
              f"{len(audio_files)} episodes")

        return {
            'statusCode': 200,
            'body': json.dumps(
                f'RSS feed updated with {len(audio_files)} episodes'
            )
        }

    except Exception as e:
        print(f"Error generating RSS feed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


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
        f'Copyright {datetime.now().year} {podcast_author}')
    ET.SubElement(channel, 'managingEditor').text = podcast_email
    ET.SubElement(channel, 'webMaster').text = podcast_email
    ET.SubElement(channel, 'lastBuildDate').text = (
        datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT'))
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


def extract_date_from_filename(filename):
    """
    Extract date from filename in formats like:
    - MM_DD_YYYY (e.g., 12_10_2025)
    - MM-DD-YYYY (e.g., 12-10-2025)
    Returns datetime object or None if not found.
    """
    # Get just the filename without path
    basename = os.path.basename(filename)
    
    # Try to find date patterns: MM_DD_YYYY or MM-DD-YYYY
    # Look for patterns like: 12_10_2025, 12-10-2025, etc.
    # Prefer MM-DD-YYYY format (most common in filenames)
    patterns = [
        r'(\d{1,2})[_-](\d{1,2})[_-](\d{4})',  # MM_DD_YYYY or MM-DD-YYYY
        r'(\d{4})[_-](\d{1,2})[_-](\d{1,2})',  # YYYY_MM_DD or YYYY-MM-DD
    ]
    
    for pattern in patterns:
        matches = list(re.finditer(pattern, basename))
        # Use the last match (most likely to be the episode date, not year in title)
        if matches:
            match = matches[-1]
            try:
                if len(match.group(3)) == 4:  # MM_DD_YYYY format
                    month = int(match.group(1))
                    day = int(match.group(2))
                    year = int(match.group(3))
                else:  # YYYY_MM_DD format
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                
                # Validate date ranges
                if 1 <= month <= 12 and 1 <= day <= 31 and year >= 1900 and year <= 2100:
                    # Additional validation: check if day is valid for the month
                    try:
                        return datetime(year, month, day)
                    except ValueError:
                        # Invalid date (e.g., Feb 30)
                        continue
            except (ValueError, IndexError, AttributeError):
                continue
    
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


def get_audio_metadata(s3_client, bucket_name, key):
    """
    Get duration and publication date from audio file metadata
    Returns tuple: (duration in seconds, publication datetime or None)
    """
    temp_file = None
    try:
        # Download file to temporary location
        temp_file = f'/tmp/{os.path.basename(key)}'
        s3_client.download_file(bucket_name, key, temp_file)
        
        # Get metadata using mutagen
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
                print(f"Error reading ID3 tags for {key}: {str(e)}")
        
        # For MP4/M4A files, check metadata
        elif isinstance(audio_file, MP4):
            try:
                if audio_file.tags is not None:
                    # Check for date tag
                    if '\xa9day' in audio_file.tags:
                        date_str = str(audio_file.tags['\xa9day'][0])
                        pub_date = parse_id3_date(date_str)
            except Exception as e:
                print(f"Error reading MP4 tags for {key}: {str(e)}")
        
        # Clean up temp file
        os.remove(temp_file)
        return (duration, pub_date)
        
    except Exception as e:
        print(f"Error getting metadata for {key}: {str(e)}")
        # Clean up temp file if it exists
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
        return (0, None)


def parse_id3_date(date_str):
    """
    Parse various date formats from ID3 tags
    Returns datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    
    # Try common date formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2024-12-10 14:30:00
        '%Y-%m-%dT%H:%M:%S',  # 2024-12-10T14:30:00
        '%Y-%m-%d',           # 2024-12-10
        '%Y/%m/%d',           # 2024/12/10
        '%d-%m-%Y',           # 10-12-2024
        '%m/%d/%Y',           # 12/10/2024
        '%Y',                 # Just year
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try parsing year only
    try:
        year = int(date_str[:4])
        return datetime(year, 1, 1)
    except (ValueError, IndexError):
        pass
    
    return None


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

