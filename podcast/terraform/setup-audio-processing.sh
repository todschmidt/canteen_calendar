#!/bin/bash

# Setup script for audio processing dependencies
# This script helps install the required tools and Python packages
# Optimized for Git Bash on Windows

set -e

echo "🎵 Cedar Mountain Podcast Audio Processing Setup"
echo "================================================"
echo "Running under Git Bash on Windows"
echo ""

# Check Python version (try both python and python3)
echo "🐍 Checking Python version..."
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "✅ Python found: $(python --version)"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "✅ Python3 found: $(python3 --version)"
else
    echo "❌ Python not found. Please install Python 3.8 or higher."
    echo "   Download from: https://www.python.org/downloads/"
    echo "   Make sure to check 'Add Python to PATH' during installation"
    exit 1
fi

# Check pip
echo "📦 Checking pip..."
$PYTHON_CMD -m pip --version || {
    echo "❌ pip not found. Please install pip."
    echo "   Usually comes with Python installation"
    exit 1
}

# Install Python dependencies
echo "📚 Installing Python dependencies..."
$PYTHON_CMD -m pip install -r requirements-audio.txt

# Check FFmpeg
echo "🎬 Checking FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg found: $(ffmpeg -version | head -n1)"
else
    echo "❌ FFmpeg not found!"
    echo ""
    echo "Please install FFmpeg for Windows:"
    echo ""
    echo "Option 1 - Download Pre-built Binary:"
    echo "  1. Go to https://ffmpeg.org/download.html"
    echo "  2. Click 'Windows' → 'Windows builds by BtbN'"
    echo "  3. Download 'ffmpeg-master-latest-win64-gpl.zip'"
    echo "  4. Extract to C:\\ffmpeg"
    echo "  5. Add C:\\ffmpeg\\bin to your Windows PATH:"
    echo "     - Open System Properties → Environment Variables"
    echo "     - Edit PATH variable"
    echo "     - Add: C:\\ffmpeg\\bin"
    echo "  6. Restart Git Bash"
    echo ""
    echo "Option 2 - Using Chocolatey (if installed):"
    echo "  choco install ffmpeg"
    echo ""
    echo "Option 3 - Using Scoop (if installed):"
    echo "  scoop install ffmpeg"
    echo ""
    echo "After installing FFmpeg, restart Git Bash and run this script again."
    exit 1
fi

# Check AWS CLI
echo "☁️  Checking AWS CLI..."
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI found: $(aws --version)"
else
    echo "❌ AWS CLI not found!"
    echo ""
    echo "Please install AWS CLI for Windows:"
    echo ""
    echo "Option 1 - MSI Installer (Recommended):"
    echo "  1. Download from: https://awscli.amazonaws.com/AWSCLIV2.msi"
    echo "  2. Run the installer"
    echo "  3. Restart Git Bash"
    echo ""
    echo "Option 2 - Using Chocolatey:"
    echo "  choco install awscli"
    echo ""
    echo "Option 3 - Using Scoop:"
    echo "  scoop install aws"
    echo ""
    echo "After installation, restart Git Bash and run this script again."
    exit 1
fi

# Test AWS credentials
echo "🔐 Testing AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials configured"
else
    echo "❌ AWS credentials not configured"
    echo "Please run: aws configure"
    exit 1
fi

echo ""
echo "🎉 Setup complete! You're ready to process audio files."
echo ""
echo "Usage examples:"
echo "  $PYTHON_CMD audio-processor.py episode1.wav --title 'Community News Update'"
echo "  $PYTHON_CMD audio-processor.py episode1.wav --title 'Weekly Update' --description 'This week\\'s news'"
echo ""
echo "For help: $PYTHON_CMD audio-processor.py --help"
echo ""
echo "💡 Note: If you encounter permission issues, you may need to run:"
echo "   chmod +x audio-processor.py"
