# Podcast Script to Google Docs Converter

This script converts the current podcast script (`podcast/current_news_script.md`) into a formatted Google Docs document for the current week.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Google API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Docs API and Google Drive API
4. Create credentials:
   - Go to "Credentials" in the left sidebar
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the credentials file and rename it to `credentials.json`
   - Place it in the same directory as the script

### 3. First Run
When you run the script for the first time:
1. It will open a browser window for Google authentication
2. Sign in with your Google account
3. Grant the necessary permissions
4. The script will save your credentials in `token.pickle` for future use

## Usage

```bash
python create_podcast_sheet.py
```

## What the Script Does

1. **Extracts** the date from `podcast/cm_community_news.txt` (e.g., "THURSDAY 8-7-25")
2. **Reads** the current podcast script from `podcast/current_news_script.md`
3. **Authenticates** with Google APIs using OAuth 2.0
4. **Finds or creates** the target folder: "Shared with me/Newscast/[Month Day, Year]"
5. **Creates** a new Google Docs document with the title: "Cedar Mountain Community Podcast Script - [Month Day, Year]"
6. **Formats** the content for easy reading:
   - Main title in large, bold text
   - Section headers in bold
   - Content properly formatted as paragraphs
   - Professional document styling
7. **Outputs** the document URL and file information

## Output

The script will create a well-formatted Google Docs document with:
- Proper section breaks
- Bold headers
- Professional paragraph formatting
- Clean document styling
- Easy-to-read layout

## Troubleshooting

- **"Folder not found"**: The script will automatically create the "Newscast" and date-specific folders if they don't exist
- **"Date not found"**: Make sure the community news file contains a date in the format "FOR [DAY] [M]-[D]-[YY]"
- **Authentication errors**: Delete `token.pickle` and run the script again
- **Permission errors**: Ensure your Google account has access to the target folder

## Files Created

- `credentials.json` - Google API credentials (you need to create this)
- `token.pickle` - Authentication token (created automatically)
- Google Docs document in the specified folder 