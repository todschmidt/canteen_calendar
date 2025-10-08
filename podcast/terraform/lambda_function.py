import json
import boto3
import os
from datetime import datetime
import xml.etree.ElementTree as ET


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

        # Filter for audio files and sort by last modified date
        audio_files = []
        for obj in response['Contents']:
            key = obj['Key']
            if key.lower().endswith(('.mp3', '.m4a', '.wav', '.aac')):
                audio_files.append({
                    'key': key,
                    'last_modified': obj['LastModified'],
                    'size': obj['Size']
                })

        # Sort by last modified date (newest first)
        audio_files.sort(key=lambda x: x['last_modified'], reverse=True)

        # Generate RSS feed
        rss_content = generate_rss_feed(
            audio_files,
            base_url,
            podcast_title,
            podcast_description,
            podcast_author,
            podcast_email
        )

        # Upload RSS feed to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key='rss.xml',
            Body=rss_content,
            ContentType='application/rss+xml',
            CacheControl='max-age=300'  # Cache for 5 minutes
        )

        print(f"RSS feed generated successfully with "
              f"{len(audio_files)} episodes")

        return {
            'statusCode': 200,
            'body': json.dumps(f'RSS feed updated with '
                              f'{len(audio_files)} episodes')
        }

    except Exception as e:
        print(f"Error generating RSS feed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


def generate_rss_feed(audio_files, base_url, podcast_title,
                      podcast_description, podcast_author, podcast_email):
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
    ET.SubElement(channel, 'itunes:owner').text = podcast_author
    ET.SubElement(channel, 'itunes:email').text = podcast_email
    ET.SubElement(channel, 'itunes:explicit').text = 'no'
    ET.SubElement(channel, 'itunes:category').text = 'Society & Culture'

    # Add episodes
    for i, audio_file in enumerate(audio_files):
        item = ET.SubElement(channel, 'item')

        # Generate episode title from filename
        episode_title = generate_episode_title(audio_file['key'])
        ET.SubElement(item, 'title').text = episode_title

        # Generate episode description
        episode_description = generate_episode_description(
            audio_file['key'], audio_file['last_modified'])
        ET.SubElement(item, 'description').text = episode_description

        # Generate GUID (unique identifier)
        guid = f"{base_url}/episode/{i+1}"
        guid_elem = ET.SubElement(item, 'guid')
        guid_elem.text = guid
        guid_elem.set('isPermaLink', 'false')

        # Publication date
        pub_date = audio_file['last_modified'].strftime(
            '%a, %d %b %Y %H:%M:%S GMT')
        ET.SubElement(item, 'pubDate').text = pub_date

        # Enclosure (audio file)
        enclosure = ET.SubElement(item, 'enclosure')
        enclosure.set('url', f"{base_url}/{audio_file['key']}")
        enclosure.set('length', str(audio_file['size']))
        enclosure.set('type', get_mime_type(audio_file['key']))

        # iTunes specific item tags
        ET.SubElement(item, 'itunes:title').text = episode_title
        ET.SubElement(item, 'itunes:summary').text = episode_description
        ET.SubElement(item, 'itunes:duration').text = '00:00:00'
        ET.SubElement(item, 'itunes:explicit').text = 'no'

    # Convert to string
    return ET.tostring(rss, encoding='unicode', xml_declaration=True)


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


def generate_episode_description(filename, last_modified):
    """
    Generate a description for the episode
    """
    return (f"Episode from {last_modified.strftime('%B %d, %Y')} - "
            f"{generate_episode_title(filename)}")


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

