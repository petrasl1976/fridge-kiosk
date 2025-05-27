#!/usr/bin/env python3
"""
Date Time Plugin - Main API handler
Provides current date and time data
"""
import os
import json
import datetime
import logging
from pathlib import Path

# Create a custom logger
logger = logging.getLogger(__name__)

# Load config to get logging level
config_path = Path(__file__).parent / "config.json"
try:
    with open(config_path) as f:
        config = json.load(f)
        log_level = config.get('logging', 'DEBUG')
        if log_level == 'OFF':
            logger.setLevel(logging.CRITICAL)  # Only show critical errors
        else:
            logger.setLevel(getattr(logging, log_level))
except Exception as e:
    logger.setLevel(logging.DEBUG)  # Default to DEBUG if config can't be loaded
    logger.error(f"Could not load logging config: {e}")

# Force a log message to verify logging is working
logger.info("Date Time Plugin Loaded")

# Plugin information
PLUGIN_NAME = "date-time"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Display current time and date with large digits"

def load_config():
    """Load the plugin configuration"""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(plugin_dir, 'config.json')
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def get_formatted_datetime(config=None):
    """
    Get formatted date and time according to configuration
    
    Args:
        config: Full plugin configuration (optional)
        
    Returns:
        Dictionary with formatted time and date
    """
    now = datetime.datetime.now()
    
    # Load config if not provided
    if config is None:
        config = load_config()
    
    # Extract format configuration
    format_config = config.get('format', {})
    
    return {
        'time': now.strftime(format_config.get('time', '%H:%M')),
        'date': now.strftime(format_config.get('date', '%Y.%m.%d'))
    }

def init(config):
    """
    Initialize the plugin with configuration.
    This is called by the backend when the plugin is loaded.
    
    Returns:
        Dictionary with initial data for frontend
    """
    formatted_data = get_formatted_datetime(config)
    
    # Return data for the frontend
    return {
        'data': formatted_data
    }

def api_data():
    """
    API handler to get the current date and time.
    This is the endpoint for /api/plugins/date-time/data
    
    Returns:
        Dictionary with formatted time and date
    """
    # Return formatted time and date
    return get_formatted_datetime()

# For testing directly
if __name__ == "__main__":
    print(api_data()) 