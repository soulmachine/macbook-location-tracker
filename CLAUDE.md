# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MacBook Location Tracker is a Python-based background service that continuously tracks and logs MacBook's geographic location and public IP address to MongoDB. It runs as a macOS LaunchAgent daemon, collecting location data every 5 minutes using CoreLocationCLI.

## Key Commands

### Installation and Setup
```bash
# Quick install (interactive - prompts for MongoDB URI)
./install.sh

# Manual dependency installation
brew install corelocationcli
pip install -r requirements.txt

# Test location access
/opt/homebrew/bin/corelocationcli --json
```

### Service Management
```bash
# Check service status
launchctl list | grep com.user.mylocation

# Stop service
launchctl stop com.user.mylocation
launchctl unload ~/Library/LaunchAgents/com.user.mylocation.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.user.mylocation.plist
launchctl start com.user.mylocation

# Uninstall completely
./uninstall.sh
```

### Monitoring and Debugging
```bash
# View logs
tail -f /tmp/mylocation.log      # Standard output
tail -f /tmp/mylocation.err      # Error output
tail -f /tmp/location-*.log      # Application logs with timestamps

# Manual testing (requires MONGODB_URI env var)
MONGODB_URI="your_connection_string" python3 location.py
```

## Architecture

### Core Components

1. **location.py**: Main service script that:
   - Runs continuously with 5-minute intervals (INTERVAL=300)
   - Uses device serial number for unique collection naming
   - Collects location via CoreLocationCLI subprocess
   - Fetches public IP from checkip.amazonaws.com
   - Stores data in MongoDB with automatic retry logic
   - Logs errors to separate MongoDB collection

2. **LaunchAgent Configuration**: 
   - Service runs at login via `com.user.mylocation.plist`
   - Auto-restarts on failure (KeepAlive=true)
   - MongoDB URI passed via environment variable

### Data Flow

1. LaunchAgent starts location.py at system login
2. Script gets MacBook serial number for unique identification
3. Every 5 minutes:
   - Calls `/opt/homebrew/bin/corelocationcli --json` for GPS data
   - Fetches public IP from AWS endpoint
   - Combines data and inserts into MongoDB collection
4. Errors logged to both file system and MongoDB error collection

### MongoDB Structure

- **Database**: `macbook_location`
- **Collections**: 
  - `location_{serial_number}` - Location data
  - `error_{serial_number}` - Error logs
- **Document Schema**: Contains timestamp, lat/long, accuracy, altitude, address, public_ip

## Important Implementation Details

- **MongoDB Connection**: Uses PyMongo with 3 retry attempts and 2-second delays
- **Error Handling**: Errors logged to MongoDB error collection and continue running
- **Location Permissions**: Requires macOS location services permission for Terminal/corelocationcli
- **Python Path**: Installation script auto-detects Python path using `whereis python`
- **CoreLocationCLI Path**: Hardcoded to `/opt/homebrew/bin/corelocationcli`
- **Logging**: Creates timestamped log files in /tmp/ directory