#!/usr/bin/env python3
"""
Sensors Plugin - Display temperature and humidity data from sensors and CPU
"""
import os
import json
import time
import logging
from pathlib import Path
from flask import Blueprint, render_template, jsonify

# Plugin information
PLUGIN_NAME = "sensors"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Display temperature and humidity data from sensors and CPU"

# Set up logging
logger = logging.getLogger(f"plugin.{PLUGIN_NAME}")

# Global variables
config = {}
last_data = {}
last_update_time = 0

def setup(app):
    """
    Set up the sensors plugin.
    
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
        # Default configuration
        config = {
            "position": {
                "landscape": {
                    "top": "60px",
                    "right": "10px",
                    "width": "auto",
                    "height": "auto",
                    "z_index": 10
                },
                "portrait": {
                    "top": "60px",
                    "right": "10px",
                    "width": "auto",
                    "height": "auto",
                    "z_index": 10
                }
            },
            "thresholds": {
                "cpu_temp": {
                    "warning": 60,
                    "critical": 70
                },
                "temperature": {
                    "min_normal": 18,
                    "max_normal": 25,
                    "min_warning": 15,
                    "max_warning": 28
                },
                "humidity": {
                    "min_normal": 40,
                    "max_normal": 60,
                    "min_warning": 30,
                    "max_warning": 70
                }
            },
            "refresh_interval": 60,
            "show_cpu_temp": True,
            "show_room_temp": True,
            "show_humidity": True
        }
        
        # Save default configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
    
    # Register the plugin blueprint
    blueprint = Blueprint(PLUGIN_NAME, __name__)
    
    @blueprint.route(f'/api/plugins/{PLUGIN_NAME}/data')
    def get_sensor_data():
        """
        Get the latest sensor data.
        
        Returns:
            JSON response with sensor data
        """
        global last_data, last_update_time
        
        # Check if we need to refresh the data
        current_time = time.time()
        if current_time - last_update_time > config.get('refresh_interval', 60):
            last_data = fetch_sensor_data()
            last_update_time = current_time
        
        return jsonify(last_data)
    
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
    
    # Fetch initial sensor data
    sensor_data = fetch_sensor_data()
    
    return {
        'config': config,
        'data': sensor_data,
        'view': 'view.html',
        'script': 'static/script.js',
        'style': 'static/style.css'
    }

def cleanup():
    """Clean up any resources used by the plugin."""
    logger.info(f"Cleaning up {PLUGIN_NAME} plugin")
    return True

def fetch_sensor_data():
    """
    Fetch sensor data from system and external sensors.
    
    Returns:
        Dictionary with sensor data
    """
    result = {
        'cpu_temp': get_cpu_temperature(),
        'temperature': None,
        'humidity': None,
        'error': None,
        'timestamp': time.time()
    }
    
    # Try to get temperature and humidity from BroadLink sensor if available
    try:
        broadlink_data = get_broadlink_data()
        if broadlink_data:
            result['temperature'] = broadlink_data.get('temperature')
            result['humidity'] = broadlink_data.get('humidity')
            if 'error' in broadlink_data:
                result['error'] = broadlink_data['error']
    except Exception as e:
        logger.error(f"Error getting BroadLink data: {e}")
        result['error'] = str(e)
    
    return result

def get_cpu_temperature():
    """
    Get the CPU temperature.
    
    Returns:
        CPU temperature as a float, or None if not available
    """
    try:
        # Try to read from thermal zone 0
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            return round(temp, 1)
    except Exception as e:
        logger.error(f"Error reading CPU temperature: {e}")
        return None

def get_broadlink_data():
    """
    Get temperature and humidity data from BroadLink device.
    
    Returns:
        Dictionary with temperature and humidity, or error message
    """
    try:
        # Import BroadLink module only when needed
        import broadlink
        
        devices = broadlink.discover(timeout=5)
        for device in devices:
            # Filter to find RM4 devices
            if device.type.startswith('RM4'):
                device.auth()
                sensor_data = device.check_sensors()
                return sensor_data
        
        # No devices found
        return {
            'temperature': None,
            'humidity': None,
            'error': 'No BroadLink devices found'
        }
    
    except ImportError:
        logger.error("BroadLink module not installed")
        return {
            'temperature': None,
            'humidity': None,
            'error': 'BroadLink module not installed'
        }
    except Exception as e:
        logger.error(f"Error accessing BroadLink device: {e}")
        return {
            'temperature': None,
            'humidity': None,
            'error': str(e)
        } 