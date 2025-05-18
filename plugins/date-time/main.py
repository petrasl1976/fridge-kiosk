#!/usr/bin/env python3
"""
Date Time Plugin - Main API handler
Provides current date and time data
"""
import os
import json
import datetime

def load_config():
    """Load the plugin configuration"""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(plugin_dir, 'config.json')
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config

def api_data():
    """
    API handler to get the current date and time.
    This is the endpoint for /api/plugins/date-time/data
    
    Returns:
        Dictionary with formatted time and date
    """
    config = load_config()
    now = datetime.datetime.now()
    
    # Get the format configuration
    format_config = config.get('format', {})
    
    # Return formatted time and date
    return {
        'time': now.strftime(format_config.get('time', '%H:%M')),
        'date': now.strftime(format_config.get('date', '%Y.%m.%d'))
    }

# For testing directly
if __name__ == "__main__":
    print(api_data()) 