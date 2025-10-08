#!/bin/bash

# Setup script to integrate Cygwin binaries with Git Bash
# This script helps configure your Git Bash environment to use Cygwin tools

echo "🔧 Cygwin Integration Setup for Git Bash"
echo "=========================================="
echo ""

# Detect Cygwin installation
CYGWIN_PATHS=(
    "/cygdrive/c/cygwin64/bin"
    "/cygdrive/c/cygwin/bin"
    "/cygdrive/c/cygwin64/usr/local/bin"
    "/cygdrive/c/cygwin/usr/local/bin"
)

CYGWIN_FOUND=""
for path in "${CYGWIN_PATHS[@]}"; do
    if [ -d "$path" ]; then
        CYGWIN_FOUND="$path"
        echo "✅ Found Cygwin installation at: $path"
        break
    fi
done

if [ -z "$CYGWIN_FOUND" ]; then
    echo "❌ Cygwin not found in standard locations."
    echo ""
    echo "Please install Cygwin first:"
    echo "1. Download from: https://www.cygwin.com/"
    echo "2. Install with packages you need (ffmpeg, curl, etc.)"
    echo "3. Run this script again"
    exit 1
fi

# Check if already in PATH
if echo "$PATH" | grep -q "$CYGWIN_FOUND"; then
    echo "✅ Cygwin already in PATH"
else
    echo "📝 Adding Cygwin to PATH..."
    
    # Create or update .bashrc
    BASHRC_FILE="$HOME/.bashrc"
    if [ ! -f "$BASHRC_FILE" ]; then
        touch "$BASHRC_FILE"
    fi
    
    # Add Cygwin to PATH if not already there
    if ! grep -q "cygwin" "$BASHRC_FILE"; then
        echo "" >> "$BASHRC_FILE"
        echo "# Cygwin integration" >> "$BASHRC_FILE"
        echo "export PATH=\"$CYGWIN_FOUND:\$PATH\"" >> "$BASHRC_FILE"
        echo "✅ Added Cygwin to PATH in $BASHRC_FILE"
    else
        echo "✅ Cygwin PATH already configured in $BASHRC_FILE"
    fi
    
    # Apply changes to current session
    export PATH="$CYGWIN_FOUND:$PATH"
    echo "✅ PATH updated for current session"
fi

# Test some common Cygwin tools
echo ""
echo "🧪 Testing Cygwin tools..."
echo ""

TOOLS_TO_TEST=("curl" "wget" "ffmpeg" "git" "make" "gcc")

for tool in "${TOOLS_TO_TEST[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo "✅ $tool: $(which $tool)"
    else
        echo "❌ $tool: not found"
    fi
done

# Show available packages
echo ""
echo "📦 Available Cygwin packages (sample):"
if command -v cygcheck &> /dev/null; then
    cygcheck -c | head -10
else
    echo "Run 'cygcheck -c' to see all installed packages"
fi

echo ""
echo "🎉 Cygwin integration setup complete!"
echo ""
echo "💡 Tips:"
echo "- Restart Git Bash to ensure all changes take effect"
echo "- Use 'cygcheck -c' to see installed packages"
echo "- Install new packages with Cygwin Setup.exe"
echo "- Some tools may have different names (e.g., 'curl.exe')"
echo ""
echo "🔧 To install additional packages:"
echo "1. Run Cygwin Setup.exe"
echo "2. Search for packages you need"
echo "3. Select and install"
echo "4. Restart Git Bash"
