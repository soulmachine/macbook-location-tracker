#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyicloud>=2.1.0",
#     "pytz"
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

# Dynamic interval configuration (in minutes)
MIN_POLL_INTERVAL = 1  # minimum 1 minute
MAX_POLL_INTERVAL_DAYTIME = 8  # maximum 8 minutes during daytime (10AM-6PM PST)
MAX_POLL_INTERVAL_NIGHTTIME = 16    # maximum 16 minutes during nighttime
DAYLIGHT_START_HOUR = 10  # 10 AM PST
DAYLIGHT_END_HOUR = 18    # 6 PM PST
LOCATION_PRECISION = 6  # decimal places for coordinate comparison

def human_time(ms):
    if not ms:
        return None
    # Apple's timestamp is in milliseconds since epoch
    return datetime.fromtimestamp(int(ms)/1000.0, tz=ZoneInfo('America/Los_Angeles')).isoformat()

def is_location_changed(prev: tuple, curr: tuple, precision: int = LOCATION_PRECISION) -> bool:
    """
    Compare two locations with specified precision to avoid false positives
    due to GPS accuracy variations
    """
    if not prev or not curr:
        return True
    return round(prev[0], precision) != round(curr[0], precision) or \
           round(prev[1], precision) != round(curr[1], precision)

def get_max_poll_interval() -> int:
    """
    Returns the maximum polling interval based on current time.
    During daylight hours (10AM-6PM PST), returns MAX_POLL_INTERVAL_DAYTIME,
    otherwise returns MAX_POLL_INTERVAL_NIGHTTIME
    """
    current_time = datetime.now(pytz.timezone('America/Los_Angeles'))
    current_hour = current_time.hour
    if DAYLIGHT_START_HOUR <= current_hour < DAYLIGHT_END_HOUR:
        return MAX_POLL_INTERVAL_DAYTIME
    return MAX_POLL_INTERVAL_NIGHTTIME

def authenticate(api):
    ''' Doc: https://github.com/picklepete/pyicloud#two-step-and-two-factor-authentication-2sa2fa '''
    if api.requires_2fa:
        logger.info("Two-factor authentication required.")
        code = input("Enter the code you received at one of your approved devices: ").strip()
        result = api.validate_2fa_code(code)
        logger.info("Code validation result: %s" % result)

        if not result:
            logger.error("Failed to verify security code")
            sys.exit(1)

        if not api.is_trusted_session:
            logger.warning("Session is not trusted. Requesting trust...")
            result = api.trust_session()
            logger.info("Session trust result %s" % result)

            if not result:
                logger.warning("Failed to request trust. You will likely be prompted for the code again in the coming weeks")
    elif api.requires_2sa:
        logger.info("Two-step authentication required. Your trusted devices are:")

        devices = api.trusted_devices
        for i, device in enumerate(devices):
            logger.info(
                "  %s: %s" % (i, device.get('deviceName',
                "SMS to %s" % device.get('phoneNumber')))
            )

        device_input = input('Which device would you like to use? [0]: ').strip()
        device_index = int(device_input) if device_input else 0
        device = devices[device_index]
        if not api.send_verification_code(device):
            logger.error("Failed to send verification code")
            sys.exit(1)

        code = input('Please enter validation code: ').strip()
        if not api.validate_verification_code(device, code):
            logger.error("Failed to verify verification code")
            sys.exit(1)
    else:
        logger.info("Already authenticated")

def main():
    parser = argparse.ArgumentParser(description="List iCloud / Find My devices and locations")
    parser.add_argument("--username", "-u", required=True, help="Apple ID (email)")
    parser.add_argument("--password", "-p", help="Apple ID password (omit to be prompted or use keyring)")
    parser.add_argument("--china", "-c", action="store_true", help="Use iCloud China (iCloud.com.cn)")
    args = parser.parse_args()

    try:
        if args.china:
            # For Chinese Apple IDs, use the China domain
            api = PyiCloudService(args.username, args.password, accept_terms=True, china_mainland=True) if args.password \
                  else PyiCloudService(args.username, accept_terms=True, china_mainland=True)
        else:
            api = PyiCloudService(args.username, args.password, accept_terms=True) if args.password \
                  else PyiCloudService(args.username, accept_terms=True)
    except Exception as e:
        logger.error(f"Login error: {e}")
        sys.exit(1)

    # Handle Apple's 2FA / 2SA authentication
    authenticate(api)

    # Track previous locations and poll intervals per device
    device_state = {}  # {device_id: {'location': (lat, lon), 'interval': minutes}}

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
                    device_id = device.data.get('id', device.data.get('name', 'unknown'))
                    current_location = (location['latitude'], location['longitude'])

                    # Initialize device state if first time
                    if device_id not in device_state:
                        device_state[device_id] = {
                            'location': None,
                            'interval': MIN_POLL_INTERVAL
                        }

                    previous_location = device_state[device_id]['location']

                    # Check if location changed
                    if is_location_changed(previous_location, current_location):
                        # Reset interval to minimum when location changes
                        device_state[device_id]['interval'] = MIN_POLL_INTERVAL
                        logger.info(f"Device {device.data['name']} moved to {current_location}")
                    else:
                        # Double the interval up to maximum when location doesn't change
                        old_interval = device_state[device_id]['interval']
                        device_state[device_id]['interval'] = min(
                            old_interval * 2,
                            get_max_poll_interval()
                        )
                        logger.info(f"Device {device.data['name']} remained at {current_location}")

                    # Update location
                    device_state[device_id]['location'] = current_location

                    # Write to file
                    location['timestamp_str'] = human_time(location['timeStamp'])
                    device.data['updated_at'] = human_time(time.time() * 1000)
                    f.write(f"{json.dumps(device.data)}\n")

        # Use the minimum interval across all devices
        if device_state:
            next_interval = min(state['interval'] for state in device_state.values())
            logger.info(f"Next poll in {next_interval} minutes")
            time.sleep(next_interval * 60)
        else:
            # No devices found, use minimum interval
            logger.warning("No devices with valid locations found")
            time.sleep(MIN_POLL_INTERVAL * 60)

if __name__ == "__main__":
    main()
