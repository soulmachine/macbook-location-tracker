#! /usr/bin/env python3

import logging
import datetime
import time
import subprocess
import json
import urllib.request
import sys
import os

from pymongo import MongoClient

INTERVAL = 300 # seconds
DATABASE_NAME = "macbook_location"

logging.basicConfig(level=logging.WARN,
                    handlers=[logging.FileHandler(
                        '/tmp/location-' + datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d-%H-%M-%S') + '.log'),
                              logging.StreamHandler()])
logger = logging.getLogger('location')

def create_client(mongodb_uri: str) -> MongoClient:
    # Create a MongoClient instance with retry logic
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            client = MongoClient(mongodb_uri)
            # Test the connection
            client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB Atlas on attempt {attempt + 1}!")
            return client
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} connection attempts failed. Last error: {e}")
                raise e

def get_public_ip()->str:
    '''Get the current public IP address.'''
    try:
        with urllib.request.urlopen('https://checkip.amazonaws.com', timeout=5) as response:
            ip = response.read().decode('utf-8').strip()
            return ip
    except Exception as e:
        logger.warning(f"Failed to get public IP: {e}")
        return None

def get_location()->str:
    '''Run the command `corelocationcli --json` to get current location.'''
    result = subprocess.run('/opt/homebrew/bin/corelocationcli --json', shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        stderr_msg = result.stderr.strip() if result.stderr else "No error message"
        error_msg = f"corelocationcli failed with exit code {result.returncode}: {stderr_msg}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def get_serial_number():
    """
    Get the MacBook's serial number using ioreg command.
    """
    try:
        result = subprocess.run('ioreg -l | grep IOPlatformSerialNumber',
                              shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            # Extract serial number from output like: |   "IOPlatformSerialNumber" = "K6N2JW336H"
            output = result.stdout.strip()
            if '"IOPlatformSerialNumber" = "' in output:
                serial = output.split('"IOPlatformSerialNumber" = "')[1].rstrip('"')
                return serial
        logger.warning("Could not get serial number")
        return None
    except Exception as e:
        logger.warning(f"Error getting serial number: {e}")
        return None

if __name__ == "__main__":
    # Get serial number and create database name
    serial_number = get_serial_number()
    if not serial_number:
        logger.error("Could not get serial number, exiting.")
        sys.exit(1)

    # Get MongoDB URI from environment variable or use default
    mongodb_uri = os.environ.get('MONGODB_URI')
    if not mongodb_uri:
        logger.error("MONGODB_URI is not set, exiting.")
        sys.exit(1)

    collection_name = f"location_{serial_number}"
    logger.info(f"Using connection: {collection_name} (serial: {serial_number})")

    while True:
        try:
            client = create_client()
            db = client.get_database(DATABASE_NAME)
            collection = db.get_collection(collection_name)
            while True:
                location_str = get_location()
                location = json.loads(location_str)

                # Add public IP to location data
                public_ip = get_public_ip()
                if public_ip:
                    location['public_ip'] = public_ip
                
                collection.insert_one(location)
                time.sleep(INTERVAL)
        except Exception as e:
            error_message = f"Error: {e}"
            logger.error(f"Error: {e}")
            error_log_collection = db.get_collection(f"error_{serial_number}")
            error_log_collection.insert_one({"error": error_message, "timestamp": datetime.datetime.now(datetime.UTC)})
            time.sleep(INTERVAL)
