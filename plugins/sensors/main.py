#!/usr/bin/env python3
"""
Sensors Plugin - Backend module
Handles sensor hardware interaction and data processing
"""

import os
import time
import json
import logging
from pathlib import Path

# Set up logging
logger = logging.getLogger('fridge-kiosk.plugins.sensors')

# Try to import hardware-specific libraries
DHT_AVAILABLE = False
try:
    import adafruit_dht
    import board
    DHT_AVAILABLE = True
    logger.info("DHT sensor library available - hardware mode enabled")
except ImportError:
    logger.info("DHT sensor library not available - running in simulation mode")

# Settings
DHT_PIN = board.D4 if DHT_AVAILABLE else None  # Default GPIO pin for DHT sensor
CACHE_FILE = Path(__file__).parent / "sensor_cache.json"
CACHE_EXPIRY = 60  # seconds

# Initialize sensor if available
dht_sensor = None
if DHT_AVAILABLE:
    try:
        dht_sensor = adafruit_dht.DHT22(DHT_PIN)
        logger.info("DHT sensor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DHT sensor: {e}")
        DHT_AVAILABLE = False

def init(config):
    """Initialize the sensors plugin"""
    logger.info("Initializing sensors plugin")
    
    # Configure from config if available
    update_interval = config.get('config', {}).get('updateInterval', 30)
    
    # Get initial readings
    readings = get_sensor_readings()
    
    # Plugin data to return
    return {
        "hardware_available": DHT_AVAILABLE,
        "readings": readings,
        "update_interval": update_interval
    }

def get_sensor_readings():
    """Get sensor readings from hardware or cache"""
    # Check if we have recent cached data
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                
            # If cache is fresh, return it
            if time.time() - cache.get('timestamp', 0) < CACHE_EXPIRY:
                logger.debug("Using cached sensor data")
                return {
                    'temperature': cache.get('temperature'),
                    'humidity': cache.get('humidity'),
                    'timestamp': cache.get('timestamp'),
                    'source': 'cache'
                }
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
    
    # Read from hardware if available
    if DHT_AVAILABLE and dht_sensor:
        try:
            # Try to read from sensor (may fail occasionally)
            temperature = dht_sensor.temperature
            humidity = dht_sensor.humidity
            
            # Sometimes the sensor returns None or implausible values
            if temperature is not None and humidity is not None:
                if -20 <= temperature <= 50 and 0 <= humidity <= 100:
                    readings = {
                        'temperature': temperature,
                        'humidity': humidity,
                        'timestamp': time.time(),
                        'source': 'hardware'
                    }
                    
                    # Cache the readings
                    try:
                        with open(CACHE_FILE, 'w') as f:
                            json.dump(readings, f)
                    except Exception as e:
                        logger.error(f"Error writing to cache: {e}")
                    
                    return readings
            
            logger.warning("Sensor returned invalid readings, using simulation")
        except Exception as e:
            logger.error(f"Error reading from sensor: {e}")
    
    # Fallback to simulation
    import random
    readings = {
        'temperature': round(random.uniform(2, 8), 1),  # Simulated refrigerator temperature
        'humidity': round(random.uniform(30, 60), 1),
        'timestamp': time.time(),
        'source': 'simulation'
    }
    
    # Cache the simulated readings
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(readings, f)
    except Exception as e:
        logger.error(f"Error writing to cache: {e}")
    
    return readings

# API Functions that can be called from the web server
def api_get_readings():
    """API endpoint to get current readings"""
    return get_sensor_readings()

def api_get_status():
    """API endpoint to get plugin status"""
    return {
        'hardware_available': DHT_AVAILABLE,
        'sensor_type': 'DHT22' if DHT_AVAILABLE else 'Simulation',
        'cache_file': str(CACHE_FILE),
        'cache_exists': CACHE_FILE.exists()
    } 