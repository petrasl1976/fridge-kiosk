#!/usr/bin/env python3
"""Date Time Plugin - Shows current date and time"""
import json
import datetime
import logging
from pathlib import Path

# Create a custom logger
logger = logging.getLogger(__name__)
logger.info(f"{Path(__file__).parent.name} Plugin Loaded")

def load_config():
    """Load the plugin configuration"""
    config_path = Path(__file__).parent / "config.json"
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            log_level = config.get('logging', 'INFO')
            if log_level == 'OFF':
                logger.setLevel(logging.CRITICAL)
            else:
                logger.setLevel(getattr(logging, log_level))
    except Exception as e:
        logger.setLevel(logging.INFO)
        logger.error(f"Could not load logging config: {e}")
        config = {}
    
    return config


def get_formatted_datetime():
    """Get formatted date and time according to configuration"""
    config = load_config()
    now = datetime.datetime.now()
    
    return {
        'time': now.strftime(config.get('format', {}).get('time', '%H:%M')),
        'date': now.strftime(config.get('format', {}).get('date', '%Y.%m.%d'))
    }

def api_data():
    """Get current date and time"""
    return get_formatted_datetime()

# For testing directly
if __name__ == "__main__":
    print(api_data()) 