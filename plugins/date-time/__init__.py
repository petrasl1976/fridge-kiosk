#!/usr/bin/env python3
"""
Date Time Plugin - Display current time and date
"""
import os
import json
import time
import logging
import datetime
from pathlib import Path
from flask import Blueprint, jsonify

# Plugin information
PLUGIN_NAME = "date-time"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Display current time and date with large digits"

# Set up logging
logger = logging.getLogger(f"plugin.{PLUGIN_NAME}")

# Global variables
config = {}

def setup(app):
    """
    Set up the date-time plugin.
    
    Args:
        app: The Flask application object
    """
    global config
    
    logger.info(f"Setting up {PLUGIN_NAME} plugin")
    
    # Get the plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load plugin config
    config_path = os.path.join(plugin_dir, 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        logger.warning(f"No configuration file found for plugin {PLUGIN_NAME}")
        config = {}
    
    # Register the plugin blueprint
    blueprint = Blueprint(PLUGIN_NAME, __name__)
    
    @blueprint.route(f'/api/plugins/{PLUGIN_NAME}/data')
    def get_date_time():
        """
        Get the current date and time.
        
        Returns:
            JSON response with date and time data
        """
        logger.info("Date-time API endpoint called")
        now = datetime.datetime.now()
        logger.debug(f"Current server time: {now}")
        
        # Format the time and date according to config
        time_format = config.get('format', {}).get('time', 'HH:MM')
        date_format = config.get('format', {}).get('date', 'YYYY.MM.DD')
        
        # Convert to appropriate format
        formatted_time = now.strftime('%H:%M') if time_format == 'HH:MM' else now.strftime('%I:%M %p')
        formatted_date = now.strftime('%Y.%m.%d')
        
        logger.info(f"Returning formatted time: {formatted_time}, date: {formatted_date}")
        
        return jsonify({
            'time': formatted_time,
            'date': formatted_date,
            'timestamp': time.time()
        })
    
    # Register the blueprint
    app.register_blueprint(blueprint)
    
    logger.info(f"{PLUGIN_NAME} plugin setup completed")
    return True

def get_routes(app):
    """
    Get the routes for this plugin.
    
    Args:
        app: The Flask application object
        
    Returns:
        List of routes used by this plugin
    """
    return [f'/api/plugins/{PLUGIN_NAME}/data']

def get_data():
    """
    Get the initial data for this plugin to be rendered in the template.
    
    Returns:
        Dictionary with plugin data
    """
    global config
    
    logger.info("Generating initial date-time data for template")
    
    # Get current date and time
    now = datetime.datetime.now()
    logger.debug(f"Current server time for template: {now}")
    time_format = config.get('format', {}).get('time', 'HH:MM')
    
    # Format the time and date
    formatted_time = now.strftime('%H:%M') if time_format == 'HH:MM' else now.strftime('%I:%M %p')
    formatted_date = now.strftime('%Y.%m.%d')
    
    logger.info(f"Initial template time: {formatted_time}, date: {formatted_date}")
    
    # Return data for the frontend
    return {
        'config': config,
        'data': {
            'time': formatted_time,
            'date': formatted_date,
            'timestamp': time.time()
        },
        'view': 'view.html',
        'script': 'static/script.js',
        'style': 'static/style.css'
    }

def cleanup():
    """Clean up any resources used by the plugin."""
    logger.info(f"Cleaning up {PLUGIN_NAME} plugin")
    return True 