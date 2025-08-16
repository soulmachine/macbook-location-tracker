#!/bin/bash

# MacBook Location Tracker Installation Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🌍 MacBook Location Tracker Installer"
echo "======================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is only for macOS${NC}"
    exit 1
fi

# Check for required dependencies
echo "📋 Checking dependencies..."

# Get Python path
PYTHON_PATH=$(whereis python3 | awk '{print $2}')
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}❌ Python not found${NC}"
    echo "Please install Python first"
    exit 1
else
    echo -e "${GREEN}✓ Python found: $PYTHON_PATH${NC}"
fi

# Check for corelocationcli
if ! command -v corelocationcli &> /dev/null; then
    echo -e "${YELLOW}⚠️  corelocationcli not found${NC}"
    echo "Installing corelocationcli via Homebrew..."
    
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}❌ Homebrew is not installed${NC}"
        echo "Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    
    brew install corelocationcli
    echo -e "${GREEN}✓ corelocationcli installed${NC}"
else
    echo -e "${GREEN}✓ corelocationcli found${NC}"
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
$PYTHON_PATH -m pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Get MongoDB URI from user
echo ""
echo "🔑 MongoDB Configuration"
echo "Please enter your MongoDB URI (e.g., mongodb+srv://username:password@cluster.mongodb.net/)"
echo -n "MongoDB URI: "
read -r MONGODB_URI

# Validate that URI was provided
if [ -z "$MONGODB_URI" ]; then
    echo -e "${RED}❌ MongoDB URI is required${NC}"
    exit 1
fi

echo -e "${GREEN}✓ MongoDB URI configured${NC}"

# Update plist file with correct paths
echo ""
echo "🔧 Configuring LaunchAgent..."

PLIST_DEST="$HOME/Library/LaunchAgents/com.user.mylocation.plist"
SCRIPT_PATH="$SCRIPT_DIR/location.py"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Create plist with correct paths
cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <!-- Unique identifier for your daemon -->
  <key>Label</key>
  <string>com.user.mylocation</string>

  <!-- Command to run your script -->
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_PATH</string>
    <string>$SCRIPT_PATH</string>
  </array>

  <!-- Run at login -->
  <key>RunAtLoad</key>
  <true/>

  <!-- Optional: Restart if the script crashes/exits -->
  <key>KeepAlive</key>
  <true/>

  <!-- Environment Variables -->
  <key>EnvironmentVariables</key>
  <dict>
    <key>MONGODB_URI</key>
    <string>$MONGODB_URI</string>
  </dict>

  <!-- Optional: Output logs to files -->
  <key>StandardOutPath</key>
  <string>/tmp/mylocation.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/mylocation.err</string>
</dict>
</plist>
EOF

echo -e "${GREEN}✓ LaunchAgent configured${NC}"

# Test location access
echo ""
echo "🔐 Testing location access..."
echo "macOS will ask for location permission if not already granted."
echo "Please allow location access when prompted."
echo ""

# Test corelocationcli
if /opt/homebrew/bin/corelocationcli --json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Location access working${NC}"
else
    echo -e "${YELLOW}⚠️  Location access may need to be granted${NC}"
    echo "You may need to grant location access in System Settings > Privacy & Security > Location Services"
fi

# Load and start the LaunchAgent
echo ""
echo "🚀 Starting location tracker..."

# Unload if already loaded (ignore errors)
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the new plist
launchctl load "$PLIST_DEST"

# Start the service
launchctl start com.user.mylocation

# Check if service is running
sleep 2
if launchctl list | grep -q com.user.mylocation; then
    echo -e "${GREEN}✓ Location tracker is running${NC}"
    
    # Get serial number for display
    SERIAL=$(ioreg -l | grep IOPlatformSerialNumber | awk -F'"' '{print $4}')
    echo ""
    echo "📊 Configuration:"
    echo "  Database: macbook_location"
    echo "  Collection: location_${SERIAL}"
    echo "  Error collection: error_${SERIAL}"
    echo "  Update interval: 5 minutes"
    echo ""
    echo "📁 Log files:"
    echo "  Standard output: /tmp/mylocation.log"
    echo "  Standard error: /tmp/mylocation.err"
    echo "  Script logs: /tmp/location-*.log"
else
    echo -e "${RED}❌ Failed to start location tracker${NC}"
    echo "Check /tmp/mylocation.err for errors"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""
echo "To check the service status:"
echo "  launchctl list | grep com.user.mylocation"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/mylocation.log"
echo "  tail -f /tmp/mylocation.err"
echo ""
echo "To stop the service:"
echo "  launchctl stop com.user.mylocation"
echo ""
echo "To uninstall:"
echo "  ./uninstall.sh"
