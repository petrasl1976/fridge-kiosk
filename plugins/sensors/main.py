#!/usr/bin/env python3
"""
Sensors Plugin - Main API handler
Provides temperature, humidity and CPU temperature data
"""
import os
import json
import time
import subprocess
from pathlib import Path

# Plugin info
PLUGIN_NAME = "sensors"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Display temperature, humidity and CPU temperature"

def load_config():
    """Load the plugin configuration"""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(plugin_dir, 'config.json')
    
    with open(config_path, 'r') as f:
        return json.load(f)

def get_sensor_data(config=None):
    """
    Get sensor data including temperature, humidity and CPU temperature
    
    Returns:
        Dictionary with sensor data
    """
    # Default result with placeholders
    result = {
        "temperature": None,
        "humidity": None,
        "cpu_temp": None,
        "timestamp": time.time()
    }
    
    # Try to get temperature and humidity from sensor
    try:
        # Try to use BroadLink sensor first
        try:
            import broadlink
            devices = broadlink.discover(timeout=5)
            for device in devices:
                if device.type.startswith('RM4'):
                    device.auth()
                    sensor_data = device.check_sensors()
                    if sensor_data:
                        result["temperature"] = sensor_data.get("temperature")
                        result["humidity"] = sensor_data.get("humidity")
                        if result["temperature"] is not None and result["humidity"] is not None:
                            break  # Successfully got the data
        except ImportError:
            pass  # BroadLink not available

        # If BroadLink failed, try DHT22 sensor
        if result["temperature"] is None or result["humidity"] is None:
            try:
                import Adafruit_DHT
                # Read data from DHT22 sensor on GPIO pin 4
                humidity, temperature = Adafruit_DHT.read_retry(22, 4)
                if humidity is not None and temperature is not None:
                    result["temperature"] = round(temperature, 1)
                    result["humidity"] = round(humidity, 1)
                else:
                    result["temperature"] = "err"
                    result["humidity"] = "err"
            except ImportError:
                result["temperature"] = "err"
                result["humidity"] = "err"
            except Exception as e:
                print(f"Error reading temperature/humidity sensor: {e}")
                result["temperature"] = "err"
                result["humidity"] = "err"
    except Exception as e:
        print(f"Error reading temperature/humidity sensor: {e}")
    
    # Get CPU temperature
    try:
        cpu_temp = get_cpu_temperature()
        result["cpu_temp"] = cpu_temp
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")
    
    return result

def get_cpu_temperature():
    """Get CPU temperature on Raspberry Pi"""
    try:
        # Method 1: Try to read from thermal_zone0
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read()) / 1000.0
                return round(temp, 1)
                
        # Method 2: Try using vcgencmd (Raspberry Pi only)
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
        if result.returncode == 0:
            temp_text = result.stdout.strip()
            temp = float(temp_text.replace('temp=', '').replace('\'C', ''))
            return round(temp, 1)
        
        # Fallback to dummy data when not on Raspberry Pi
        if os.environ.get('FLASK_ENV') != 'production':
            return 45.6
        return None
    except Exception as e:
        print(f"Error getting CPU temperature: {e}")
        return None

def init(config):
    """
    Initialize the plugin with configuration.
    This is called by the backend when the plugin is loaded.
    
    Returns:
        Dictionary with initial data for frontend
    """
    # Get initial sensor readings
    sensor_data = get_sensor_data(config)
    
    # Return data for frontend
    return {
        'data': sensor_data
    }

def api_data():
    """
    API handler to get current sensor data.
    This is the endpoint for /api/plugins/sensors/data
    
    Returns:
        Dictionary with sensor data
    """
    # Return formatted sensor data
    return get_sensor_data() 