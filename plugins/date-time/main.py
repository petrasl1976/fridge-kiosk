#!/usr/bin/env python3
"""
Date Time Plugin - Main API handler
Provides current date and time data
"""
import os
import json
import time
import logging
import datetime
from pathlib import Path

# Set up logging
logger = logging.getLogger("plugin.date-time")

def load_config():
    """Load the plugin configuration"""
    config = {}
    # Get the plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load plugin config
    config_path = os.path.join(plugin_dir, 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.debug(f"Loaded date-time plugin config from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    else:
        logger.warning(f"No configuration file found at {config_path}")
    
    return config

def api_data():
    """
    API handler to get the current date and time.
    This is the endpoint for /api/plugins/date-time/data
    
    Returns:
        Dictionary with formatted time and date
    """
    logger.info("Date-time API endpoint called via main.py")
    
    # Always return the same structure in all cases:
    # {
    #    'error': null or error message,
    #    'time': formatted time or error message,
    #    'date': formatted date or error message,
    #    'timestamp': current timestamp
    # }
    response = {
        'error': None,
        'time': "missing format",
        'date': "missing format",
        'timestamp': time.time()
    }
    
    config = load_config()
    now = datetime.datetime.now()
    logger.debug(f"Current server time: {now}")
    
    # Get the format configuration section
    format_config = config.get('format', {})
    
    # Check if time format exists and format the time
    if 'time' not in format_config:
        error_msg = "Time format undefined in configuration"
        logger.error(error_msg)
        response['error'] = error_msg
    else:
        time_format = format_config['time']
        logger.info(f"Using time format: '{time_format}'")
        try:
            response['time'] = now.strftime(time_format)
        except Exception as e:
            error_msg = f"Error formatting time: {str(e)}"
            logger.error(error_msg)
            response['error'] = error_msg
    
    # Check if date format exists and format the date
    if 'date' not in format_config:
        error_msg = "Date format undefined in configuration"
        logger.error(error_msg)
        response['error'] = response['error'] or error_msg
    else:
        date_format = format_config['date']
        logger.info(f"Using date format: '{date_format}'")
        try:
            response['date'] = now.strftime(date_format)
        except Exception as e:
            error_msg = f"Error formatting date: {str(e)}"
            logger.error(error_msg)
            response['error'] = response['error'] or error_msg
    
    logger.info(f"Returning response: {response}")
    return response

# For testing directly
if __name__ == "__main__":
    print(api_data()) 