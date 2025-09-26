#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyicloud",
#     "pytz",
# ]
# ///
"""
Find My Devices Location Tracker

Retrieves location and status information for all devices associated with an Apple ID
using the Find My service. Supports both international and Chinese iCloud accounts.

Usage:
    # International iCloud account
    python find_my_via_icloud.py -u email@example.com -p password

    # Chinese iCloud account (iCloud.com.cn)
    python find_my_via_icloud.py -u email@example.com -p password --china

    # Omit password to be prompted (more secure)
    python find_my_via_icloud.py -u email@example.com --china
"""
import argparse
import json
import logging
import os
import pytz
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pyicloud import PyiCloudService  # pip install pyicloud

# Setup logging with LA timezone
LOG_FILE = os.getenv('LOG_FILE', 'find_my.log')
logging.Formatter.converter = lambda self, t: datetime.fromtimestamp(t, tz=pytz.timezone('America/Los_Angeles')).timetuple()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

INTERVAL = 300 # in seconds

def human_time(ms):
    if not ms:
        return None
    # Apple's timestamp is in milliseconds since epoch
    return datetime.fromtimestamp(int(ms)/1000.0, tz=ZoneInfo('America/Los_Angeles')).isoformat()

def require_2fa(api):
    if api.requires_2fa:
        logger.info("Two-factor authentication required.")
        code = input("Enter the 2FA code sent to your device: ").strip()
        if not api.validate_2fa_code(code):
            logger.error("Invalid code. Exiting.")
            sys.exit(1)
        if not api.is_trusted_session:
            logger.error("Trusting session…")
            api.trust_session()

def main():
    parser = argparse.ArgumentParser(description="List iCloud / Find My devices and locations")
    parser.add_argument("--username", "-u", required=True, help="Apple ID (email)")
    parser.add_argument("--password", "-p", help="Apple ID password (omit to be prompted or use keyring)")
    parser.add_argument("--china", "-c", action="store_true", help="Use iCloud China (iCloud.com.cn)")
    args = parser.parse_args()

    try:
        if args.china:
            # For Chinese Apple IDs, use the China domain
            api = PyiCloudService(args.username, args.password, china_mainland=True) if args.password \
                  else PyiCloudService(args.username, china_mainland=True)
        else:
            api = PyiCloudService(args.username, args.password) if args.password \
                  else PyiCloudService(args.username)
    except Exception as e:
        logger.error(f"Login error: {e}")
        sys.exit(1)

    # Handle Apple's 2FA / 2SA flows (once per trust period)
    require_2fa(api)

    while True:
        # Check if Find My service is available
        logger.info("Fetching the device list")
        devices = api.devices
        # Enumerate devices
        with open("find_my.json", "a") as f:
            for device in devices:
                location = device.data['location']
                # only append devices with a valid location
                if location and location['latitude'] and location['longitude']:
                    location['timestamp_str'] = human_time(location['timeStamp'])
                    device.data['updated_at'] = human_time(time.time() * 1000)
                    f.write(f"{json.dumps(device.data)}\n")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
