# MacBook Location Tracker

A background service that continuously tracks and logs your MacBook's geographic location and public IP address to MongoDB.

## Features

- Automatic tracking every 5 minutes for both:
  - Geographic location (GPS coordinates, address)
  - Network location (public IP address)
- Stores data in MongoDB database
- Runs as a background daemon using macOS LaunchAgent
- Automatic restart on failure

## Prerequisites

- macOS (tested on macOS 14+)
- Python 3
- Homebrew
- MongoDB Database

## Quick Start

```bash
./install
```

## Appendix: Installation Manually

### 1. Clone the Repository

```bash
git clone https://github.com/soulmachine/misc.git
cd misc/macbook-location-tracker
```

### 2. Install Dependencies

Install the CoreLocation CLI tool:
```bash
brew install corelocationcli
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure MongoDB Connection

Make sure you have a Mongo DB server up and running, or use MongoDB Atlas cloud service directly. Get the MongoDB connection string and export it to `MONGODB_URI` envrionment variable.

### 4. Grant Location Permissions

Run the location CLI once to trigger the macOS permission prompt:
```bash
corelocationcli --json
```

Click "Allow" when macOS asks for location access permission.

### 5. Update LaunchAgent Configuration

Edit `com.user.mylocation.plist` and update the script path to match your installation:
```xml
<string>/path/to/your/location.py</string>
```

Replace `/path/to/your/` with the actual path where you cloned the repository.

### 6. Install LaunchAgent

Copy the plist file to LaunchAgents directory:
```bash
cp com.user.mylocation.plist ~/Library/LaunchAgents/
```

Load and start the service:
```bash
launchctl load ~/Library/LaunchAgents/com.user.mylocation.plist
launchctl start com.user.mylocation
```

### 7. Check Service Status

```bash
launchctl list | grep com.user.mylocation
```

### 8. View Logs

```bash
# Main output log
tail -f /tmp/mylocation.log

# Error log
tail -f /tmp/mylocation.err

# Application logs
tail -f /tmp/location-*.log
```

### 9. Stop the Service

```bash
launchctl stop com.user.mylocation
launchctl unload ~/Library/LaunchAgents/com.user.mylocation.plist
```

### 10. Manual Testing

Run the script manually to test:
```bash
# Using hostname as database name
python3 location.py
```

## Database Structure

The tracking data is stored in MongoDB with the following structure:

- **Database**: `macbook_location`
- **Collection**: `location_{serial_number}`
- **Document Format**:
```json
{
  "_id": "ObjectId",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "accuracy": 5.0,
  "speed": -1,
  "direction": -1,
  "altitude": 0.0,
  "verticalAccuracy": -1.0,
  "address": "San Francisco, CA",
  "public_ip": "203.0.113.42"
}
```

### Field Descriptions

- **Location Data** (from CoreLocation):
  - `latitude`, `longitude`: GPS coordinates
  - `accuracy`: Horizontal accuracy in meters
  - `altitude`: Elevation in meters
  - `address`: Reverse geocoded address
  - `timestamp`: When the location was recorded

- **Network Data**:
  - `public_ip`: Your current public IP address (useful for tracking network changes)

## Troubleshooting

### Service Not Starting

1. Check if the script path in the plist file is correct
2. Verify Python path: `which python`
3. Check logs for errors: `tail -f /tmp/mylocation.err`

### Location Permission Issues

1. Go to System Settings → Privacy & Security → Location Services
2. Find Terminal or corelocationcli in the list
3. Ensure it's enabled

### MongoDB Connection Issues

1. Verify your MongoDB Atlas cluster is running
2. Check network connectivity
3. Ensure IP whitelist includes your current IP
4. Review connection string credentials

### No Location Data

1. Ensure Wi-Fi is enabled (improves location accuracy)
2. Check if location services are enabled system-wide
3. Try running `corelocationcli --json` manually
