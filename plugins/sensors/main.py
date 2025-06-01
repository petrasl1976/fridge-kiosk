#!/usr/bin/env python3
"""Sensors Plugin - Shows temperature, humidity and CPU temperature"""
import os
import json
import time
import subprocess
from pathlib import Path
import logging

# Create a custom logger
logger = logging.getLogger(__name__)
logger.info(f"{Path(__file__).parent.name} Plugin Loaded")

# Broadlink settings
BROADLINK_DISCOVER_TIMEOUT = 5
BROADLINK_TARGET_TYPE = "RM4"

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

def get_sensor_data():
    """Get sensor data including temperature, humidity and CPU temperature"""
    result = {
        "temperature": None,
        "humidity": None,
        "cpu_temp": None
    }
    
    # Try to get temperature and humidity from sensor
    try:
        import broadlink
        devices = broadlink.discover(timeout=BROADLINK_DISCOVER_TIMEOUT)
        for device in devices:
            if device.type.startswith(BROADLINK_TARGET_TYPE):
                device.auth()
                sensor_data = device.check_sensors()
                if sensor_data:
                    result["temperature"] = sensor_data.get("temperature")
                    result["humidity"] = sensor_data.get("humidity")
                    if result["temperature"] is not None and result["humidity"] is not None:
                        break
    except Exception as e:
        logger.error(f"Error reading broadlink sensor: {e}")
    
    # Get CPU temperature
    try:
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                result["cpu_temp"] = round(temp, 1)
        else:
            result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
            if result.returncode == 0:
                temp_text = result.stdout.strip()
                temp = float(temp_text.replace('temp=', '').replace('\'C', ''))
                result["cpu_temp"] = round(temp, 1)
    except Exception as e:
        logger.error(f"Error reading CPU temperature: {e}")
    
    return result

def api_data():
    """Get current sensor data"""
    return get_sensor_data()

# For testing directly
if __name__ == "__main__":
    print(api_data()) 