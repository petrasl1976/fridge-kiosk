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
    
    config = load_config()
    now = datetime.datetime.now()
    logger.debug(f"Current server time: {now}")
    
    # Format the time and date according to config
    time_format = config.get('format', {}).get('time', 'HH:MM')
    date_format = config.get('format', {}).get('date', 'YYYY.MM.DD')
    
    # Convert to appropriate format
    formatted_time = now.strftime('%H:%M') if time_format == 'HH:MM' else now.strftime('%I:%M %p')
    formatted_date = now.strftime('%Y.%m.%d')
    
    logger.info(f"Returning formatted time: {formatted_time}, date: {formatted_date}")
    
    return {
        'time': formatted_time,
        'date': formatted_date,
        'timestamp': time.time()
    }

# For testing directly
if __name__ == "__main__":
    print(api_data()) 