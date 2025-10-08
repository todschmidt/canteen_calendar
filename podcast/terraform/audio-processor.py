#!/usr/bin/env python3
"""
Cedar Mountain Podcast Audio Processor

Converts WAV files to podcast-optimized MP3 format and uploads to S3.
Automatically extracts metadata and triggers RSS feed generation.

Usage:
    python audio-processor.py input.wav [--title "Episode Title"] [--description "Description"]
    
Note: Works with both Windows (Git Bash) and Unix-like systems.
"""

import argparse
import os
import sys
import boto3
import json
from datetime import datetime
from pathlib import Path
import subprocess
import tempfile
import shutil

# Audio processing libraries
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPE2, TCOM, TENC, COMM
except ImportError:
    print("Error: mutagen library not found. Install with: pip install mutagen")
    sys.exit(1)

# Configuration
S3_BUCKET = "cedar-mountain-podcast-dev-podcast-files"
AWS_REGION = "us-east-1"
PODCAST_TITLE = "Canteen Calendar Podcast"
PODCAST_AUTHOR = "Cedar Mountain Canteer Team"
PODCAST_EMAIL = "tschmidty@yahoo.com"

# Audio settings for podcast optimization
AUDIO_SETTINGS = {
    "bitrate": "128k",  # Good quality for speech
    "sample_rate": "44100",  # Standard sample rate
    "channels": "2",  # Stereo
    "codec": "libmp3lame",  # High-quality MP3 encoder
    "preset": "medium"  # Encoding speed vs quality balance
}


class AudioProcessor:
    """Handles audio conversion, metadata extraction, and S3 upload."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        
    def check_dependencies(self):
        """Check if required tools are installed."""
        try:
            # Check for ffmpeg
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            print("✅ FFmpeg found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ FFmpeg not found. Please install FFmpeg:")
            print("   Windows: Download from https://ffmpeg.org/download.html")
            print("   macOS: brew install ffmpeg")
            print("   Ubuntu: sudo apt install ffmpeg")
            return False
            
        return True
    
    def convert_wav_to_mp3(self, input_file, output_file):
        """Convert WAV file to MP3 with podcast-optimized settings."""
        print(f"🎵 Converting {input_file} to MP3...")
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-codec:a', AUDIO_SETTINGS['codec'],
            '-b:a', AUDIO_SETTINGS['bitrate'],
            '-ar', AUDIO_SETTINGS['sample_rate'],
            '-ac', AUDIO_SETTINGS['channels'],
            '-preset', AUDIO_SETTINGS['preset'],
            '-y',  # Overwrite output file
            output_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Conversion successful: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Conversion failed: {e.stderr}")
            return False
    
    def extract_audio_metadata(self, mp3_file):
        """Extract metadata from MP3 file."""
        try:
            audio = MP3(mp3_file)
            metadata = {
                'duration': int(audio.info.length),
                'bitrate': audio.info.bitrate,
                'sample_rate': audio.info.sample_rate,
                'channels': audio.info.channels,
                'file_size': os.path.getsize(mp3_file)
            }
            return metadata
        except Exception as e:
            print(f"❌ Error extracting metadata: {e}")
            return None
    
    def add_id3_tags(self, mp3_file, episode_title, episode_description, 
                     episode_number=None):
        """Add ID3 tags to MP3 file."""
        print(f"🏷️  Adding ID3 tags to {mp3_file}...")
        
        try:
            # Load existing tags or create new ones
            audio_file = mutagen.File(mp3_file)
            if audio_file is None:
                audio_file = MP3(mp3_file)
            
            # Add ID3 tags
            audio_file.tags = ID3()
            
            # Basic tags
            audio_file.tags.add(TIT2(encoding=3, text=episode_title))
            audio_file.tags.add(TPE1(encoding=3, text=PODCAST_AUTHOR))
            audio_file.tags.add(TALB(encoding=3, text=PODCAST_TITLE))
            audio_file.tags.add(TPE2(encoding=3, text=PODCAST_AUTHOR))
            audio_file.tags.add(TCOM(encoding=3, text=PODCAST_AUTHOR))
            audio_file.tags.add(TENC(encoding=3, text="Cedar Mountain Podcast Infrastructure"))
            
            # Date
            current_year = datetime.now().year
            audio_file.tags.add(TDRC(encoding=3, text=str(current_year)))
            
            # Genre
            audio_file.tags.add(TCON(encoding=3, text="Podcast"))
            
            # Comment with description
            audio_file.tags.add(COMM(encoding=3, lang='eng', text=episode_description))
            
            # Save tags
            audio_file.save()
            print("✅ ID3 tags added successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error adding ID3 tags: {e}")
            return False
    
    def generate_episode_filename(self, episode_title, episode_number=None):
        """Generate a clean filename for the episode."""
        # Clean the title for filename use
        clean_title = "".join(c for c in episode_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_title = clean_title.replace(' ', '_').lower()
        
        # Add episode number if provided
        if episode_number:
            filename = f"episode_{episode_number:03d}_{clean_title}.mp3"
        else:
            # Use timestamp for uniqueness
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"episode_{timestamp}_{clean_title}.mp3"
        
        return filename
    
    def upload_to_s3(self, local_file, s3_key):
        """Upload file to S3 bucket."""
        print(f"☁️  Uploading {local_file} to S3...")
        
        try:
            # Upload with metadata
            extra_args = {
                'ContentType': 'audio/mpeg',
                'Metadata': {
                    'podcast': PODCAST_TITLE,
                    'author': PODCAST_AUTHOR,
                    'upload-date': datetime.now().isoformat()
                }
            }
            
            self.s3_client.upload_file(
                local_file, 
                S3_BUCKET, 
                s3_key,
                ExtraArgs=extra_args
            )
            
            print(f"✅ Upload successful: s3://{S3_BUCKET}/{s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def format_duration(self, seconds):
        """Format duration in HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def process_audio(self, input_file, episode_title, episode_description, 
                     episode_number=None):
        """Main processing function."""
        print(f"🎙️  Processing audio file: {input_file}")
        print(f"📝 Episode Title: {episode_title}")
        print(f"📄 Description: {episode_description}")
        print("-" * 50)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Validate input file
        if not os.path.exists(input_file):
            print(f"❌ Input file not found: {input_file}")
            return False
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Generate output filename
            output_filename = self.generate_episode_filename(episode_title, episode_number)
            output_path = temp_dir_path / output_filename
            
            # Convert WAV to MP3
            if not self.convert_wav_to_mp3(input_file, str(output_path)):
                return False
            
            # Extract metadata
            metadata = self.extract_audio_metadata(str(output_path))
            if not metadata:
                return False
            
            # Add ID3 tags
            if not self.add_id3_tags(str(output_path), episode_title, 
                                   episode_description, episode_number):
                return False
            
            # Upload to S3
            if not self.upload_to_s3(str(output_path), output_filename):
                return False
            
            # Print summary
            print("\n" + "=" * 50)
            print("🎉 PROCESSING COMPLETE!")
            print("=" * 50)
            print(f"📁 Original file: {input_file}")
            print(f"📁 S3 location: s3://{S3_BUCKET}/{output_filename}")
            print(f"⏱️  Duration: {self.format_duration(metadata['duration'])}")
            print(f"📊 File size: {metadata['file_size']:,} bytes")
            print(f"🎵 Bitrate: {metadata['bitrate']} kbps")
            print(f"🔗 RSS Feed: https://cedarmountainnews.todschmidt.com/rss.xml")
            print("\n💡 The RSS feed will be automatically updated by Lambda!")
            
            return True


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Convert WAV files to podcast MP3 and upload to S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audio-processor.py episode1.wav
  python audio-processor.py episode1.wav --title "Community News Update"
  python audio-processor.py episode1.wav --title "Weekly Update" --description "This week's community news"
  python audio-processor.py episode1.wav --title "Episode 1" --number 1
        """
    )
    
    parser.add_argument('input_file', help='Input WAV file to process')
    parser.add_argument('--title', '-t', required=True, 
                       help='Episode title (required)')
    parser.add_argument('--description', '-d', 
                       help='Episode description (auto-generated if not provided)')
    parser.add_argument('--number', '-n', type=int,
                       help='Episode number for filename')
    
    args = parser.parse_args()
    
    # Generate description if not provided
    if not args.description:
        args.description = f"Episode from {datetime.now().strftime('%B %d, %Y')} - {args.title}"
    
    # Create processor and run
    processor = AudioProcessor()
    success = processor.process_audio(
        args.input_file,
        args.title,
        args.description,
        args.number
    )
    
    if success:
        print("\n🚀 Ready to submit to podcast platforms!")
        print("   RSS Feed URL: https://cedarmountainnews.todschmidt.com/rss.xml")
        sys.exit(0)
    else:
        print("\n❌ Processing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
