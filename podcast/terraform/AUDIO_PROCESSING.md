# Audio Processing & Upload Guide

This guide explains how to convert WAV files to podcast-optimized MP3 format and upload them to your S3 bucket for automatic RSS feed generation.

## 🎵 Overview

The audio processing system converts large WAV files from your provider into compressed, podcast-ready MP3 files with proper metadata and uploads them to S3. The Lambda function automatically detects new files and updates the RSS feed.

## 📋 Required Metadata for RSS Feed

### **Essential Metadata:**
- **Episode Title** - Human-readable episode name
- **Episode Description** - Brief description of episode content
- **Publication Date** - Automatically set to current timestamp
- **Duration** - Extracted from audio file (HH:MM:SS format)
- **File Size** - Required for RSS enclosure tag
- **MIME Type** - Set to `audio/mpeg` for MP3 files

### **ID3 Tags Added:**
- **Title** (TIT2) - Episode title
- **Artist** (TPE1) - Podcast author
- **Album** (TALB) - Podcast name
- **Year** (TDRC) - Current year
- **Genre** (TCON) - "Podcast"
- **Comment** (COMM) - Episode description

## 🛠️ Setup Instructions

### 1. **Install Dependencies**
```bash
# Run the setup script (works in Git Bash on Windows)
./setup-audio-processing.sh

# Or install manually:
python -m pip install -r requirements-audio.txt
```

### **Windows/Git Bash Notes:**
- The setup script is optimized for Git Bash on Windows
- It will detect whether you have `python` or `python3` available
- FFmpeg installation instructions are Windows-specific
- All paths are handled correctly for Windows environments

### 2. **Required Tools**
- **Python 3.8+** with pip
- **FFmpeg** - Audio conversion tool
- **AWS CLI** - For S3 upload
- **mutagen** - Python audio metadata library

### 3. **Verify Setup**
```bash
# Test FFmpeg
ffmpeg -version

# Test AWS credentials
aws sts get-caller-identity

# Test Python dependencies
python3 -c "import mutagen, boto3; print('Dependencies OK')"
```

## 🎙️ Usage Examples

### **Basic Usage**
```bash
# Use 'python' or 'python3' depending on your system
python audio-processor.py episode1.wav --title "Community News Update"
```

### **With Description**
```bash
python audio-processor.py episode1.wav \
  --title "Weekly Community Update" \
  --description "This week's highlights from Cedar Mountain community"
```

### **With Episode Number**
```bash
python audio-processor.py episode1.wav \
  --title "Episode 1: Welcome" \
  --number 1 \
  --description "Introduction to our community podcast"
```

### **Get Help**
```bash
python audio-processor.py --help
```

## ⚙️ Audio Processing Settings

### **Optimized for Podcasts:**
- **Bitrate**: 128 kbps (good quality for speech)
- **Sample Rate**: 44.1 kHz (standard)
- **Channels**: Stereo (2 channels)
- **Codec**: libmp3lame (high-quality MP3)
- **Preset**: medium (balanced speed vs quality)

### **File Naming Convention:**
- **With episode number**: `episode_001_community_news_update.mp3`
- **Without episode number**: `episode_20250911_1430_community_news_update.mp3`

## 📊 Processing Workflow

1. **Input Validation** - Check WAV file exists and tools are available
2. **Audio Conversion** - Convert WAV → MP3 with podcast settings
3. **Metadata Extraction** - Get duration, bitrate, file size
4. **ID3 Tagging** - Add podcast metadata to MP3
5. **S3 Upload** - Upload with proper content type and metadata
6. **RSS Generation** - Lambda automatically updates RSS feed

## 🔄 Automatic RSS Feed Updates

When you upload an MP3 file:

1. **S3 Event Trigger** - Lambda function is automatically invoked
2. **File Discovery** - Lambda scans S3 bucket for audio files
3. **RSS Generation** - Creates/updates RSS feed with new episode
4. **Metadata Extraction** - Uses ID3 tags for episode information
5. **Feed Publishing** - Updated RSS feed is available at your domain

## 📁 File Structure

```
terraform/
├── audio-processor.py          # Main processing script
├── requirements-audio.txt      # Python dependencies
├── setup-audio-processing.sh  # Setup script
└── AUDIO_PROCESSING.md        # This documentation
```

## 🎯 Output Example

```
🎙️  Processing audio file: episode1.wav
📝 Episode Title: Community News Update
📄 Description: Episode from September 11, 2025 - Community News Update
--------------------------------------------------
🎵 Converting episode1.wav to MP3...
✅ Conversion successful: episode_20250911_1430_community_news_update.mp3
🏷️  Adding ID3 tags to episode_20250911_1430_community_news_update.mp3...
✅ ID3 tags added successfully
☁️  Uploading episode_20250911_1430_community_news_update.mp3 to S3...
✅ Upload successful: s3://cedar-mountain-podcast-dev-podcast-files/episode_20250911_1430_community_news_update.mp3

==================================================
🎉 PROCESSING COMPLETE!
==================================================
📁 Original file: episode1.wav
📁 S3 location: s3://cedar-mountain-podcast-dev-podcast-files/episode_20250911_1430_community_news_update.mp3
⏱️  Duration: 00:15:30
📊 File size: 14,234,567 bytes
🎵 Bitrate: 128 kbps
🔗 RSS Feed: https://cedarmountainnews.todschmidt.com/rss.xml

💡 The RSS feed will be automatically updated by Lambda!

🚀 Ready to submit to podcast platforms!
   RSS Feed URL: https://cedarmountainnews.todschmidt.com/rss.xml
```

## 🚨 Troubleshooting

### **FFmpeg Not Found**
```bash
# Windows: Download from https://ffmpeg.org/download.html
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
```

### **AWS Credentials Error**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

### **Python Dependencies Missing**
```bash
pip install -r requirements-audio.txt
```

### **Permission Denied**
```bash
chmod +x audio-processor.py
```

## 📈 Quality Guidelines

### **Input Requirements:**
- **Format**: WAV (uncompressed)
- **Quality**: Any quality (will be optimized during conversion)
- **Size**: No limit (will be compressed significantly)

### **Output Specifications:**
- **Format**: MP3
- **Bitrate**: 128 kbps (speech-optimized)
- **Size**: Typically 1-2 MB per minute of audio
- **Compatibility**: Works with all podcast platforms

## 🔗 Next Steps

After processing your first episode:

1. **Test RSS Feed**: Visit `https://cedarmountainnews.todschmidt.com/rss.xml`
2. **Verify Episode**: Check that your episode appears in the feed
3. **Submit to Platforms**: Use the RSS feed URL to submit to:
   - Apple Podcasts Connect
   - Spotify for Podcasters
   - Google Podcasts Manager
   - Other podcast platforms

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Test with a small WAV file first
4. Check AWS credentials and permissions
