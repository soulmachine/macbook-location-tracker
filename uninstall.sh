#!/bin/bash

# MacBook Location Tracker Uninstallation Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🗑️  MacBook Location Tracker Uninstaller"
echo "========================================"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is only for macOS${NC}"
    exit 1
fi

PLIST_DEST="$HOME/Library/LaunchAgents/com.user.mylocation.plist"

echo "📋 Stopping and removing location tracker..."

# Check if service is running
if launchctl list | grep -q com.user.mylocation; then
    echo "Stopping service..."
    launchctl stop com.user.mylocation
    echo -e "${GREEN}✓ Service stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Service was not running${NC}"
fi

# Unload the LaunchAgent if loaded
if [ -f "$PLIST_DEST" ]; then
    echo "Unloading LaunchAgent..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo -e "${GREEN}✓ LaunchAgent unloaded${NC}"
    
    # Remove the plist file
    echo "Removing plist file..."
    rm "$PLIST_DEST"
    echo -e "${GREEN}✓ Plist file removed${NC}"
else
    echo -e "${YELLOW}⚠️  LaunchAgent plist not found${NC}"
fi

# Clean up log files
echo ""
echo "🧹 Cleaning up log files..."

# Remove log files
if ls /tmp/mylocation.log 2>/dev/null; then
    rm /tmp/mylocation.log
    echo -e "${GREEN}✓ Removed /tmp/mylocation.log${NC}"
fi

if ls /tmp/mylocation.err 2>/dev/null; then
    rm /tmp/mylocation.err
    echo -e "${GREEN}✓ Removed /tmp/mylocation.err${NC}"
fi

# Count and remove location-*.log files
LOG_COUNT=$(ls /tmp/location-*.log 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOG_COUNT" -gt 0 ]; then
    rm /tmp/location-*.log
    echo -e "${GREEN}✓ Removed $LOG_COUNT location log files${NC}"
else
    echo -e "${YELLOW}⚠️  No location log files found${NC}"
fi

echo ""
echo -e "${GREEN}✅ Uninstallation complete!${NC}"
echo ""
echo "Note: The following components were NOT removed:"
echo "  • Python dependencies (pymongo)"
echo "  • corelocationcli (installed via Homebrew)"
echo "  • MongoDB data"
echo "  • The location.py script and configuration files"
echo ""
echo "To remove corelocationcli:"
echo "  brew uninstall corelocationcli"
echo ""
echo "To remove Python dependencies:"
echo "  pip uninstall pymongo"