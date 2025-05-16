#!/usr/bin/env python3
"""
Sensors Plugin - Backend module
Handles sensor hardware interaction and data processing
"""

import os
import time
import json
import logging
import random
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sensors-plugin")

# Check if we can import the DHT sensor library
try:
    import Adafruit_DHT
    DHT_AVAILABLE = True
    logger.info("DHT sensor library available, using hardware sensor")
except ImportError:
    DHT_AVAILABLE = False
    logger.warning("DHT sensor library not available")

# Settings
SENSOR_TYPE = 22  # DHT22 sensor
GPIO_PIN = 4     # GPIO pin where the sensor is connected
PLUGIN_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = PLUGIN_DIR / 'data'
CACHE_FILE = DATA_DIR / 'sensor_cache.json'

# Initialize sensor if available
sensor = None
if DHT_AVAILABLE:
    try:
        sensor = Adafruit_DHT.DHT22(GPIO_PIN)
        logger.info(f"DHT22 sensor initialized on GPIO pin {GPIO_PIN}")
    except Exception as e:
        logger.error(f"Failed to initialize DHT sensor: {e}")
        DHT_AVAILABLE = False

def init(config):
    """Initialize the sensors plugin"""
    logger.info("Initializing sensors plugin")
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Get configuration
    update_interval = config.get('config', {}).get('updateInterval', 60) # seconds
    
    # Get initial readings
    readings = get_sensor_readings()
    
    return {
        "readings": readings,
        "lastUpdate": time.time(),
        "updateInterval": update_interval
    }

def get_sensor_readings():
    """Get current sensor readings from hardware or return error"""
    # First, try to read from the hardware sensor if available
    if DHT_AVAILABLE:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(SENSOR_TYPE, GPIO_PIN)
            
            # Check if the readings are valid
            if humidity is not None and temperature is not None:
                # Convert to standard format
                readings = {
                    "temperature": round(temperature, 1),
                    "humidity": round(humidity, 1),
                    "timestamp": time.time()
                }
                
                # Cache the readings
                with open(CACHE_FILE, 'w') as f:
                    json.dump(readings, f)
                
                return readings
            else:
                return {
                    "error": "Unable to read valid data from sensor",
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.error(f"Error reading from sensor: {e}")
            return {
                "error": f"Sensor reading failed: {str(e)}",
                "timestamp": time.time()
            }
    
    # If hardware reading failed or not available, return error
    return {
        "error": "No temperature sensor available",
        "timestamp": time.time()
    }

def api_get_readings():
    """API endpoint to get current sensor readings"""
    return get_sensor_readings()

def api_get_status():
    """API endpoint to get plugin status"""
    return {
        "status": "active" if DHT_AVAILABLE else "error",
        "sensor_available": DHT_AVAILABLE,
        "last_update": time.time(),
        "error": None if DHT_AVAILABLE else "Sensor hardware not available"
    } 