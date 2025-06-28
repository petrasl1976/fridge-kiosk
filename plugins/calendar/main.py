from pathlib import Path
import json
import logging
import importlib.util

# Plugin logger
logger = logging.getLogger(__name__)
logger.info("calendar Plugin Loaded")


def _get_sensor_module():
    """Dynamically import the sensors plugin to reuse its get_sensor_data implementation.
    We avoid a regular import (e.g. `import plugins.sensors.main`) because the
    `plugins` directory is not a Python package. Instead we load the module by
    absolute file path.
    Returns the imported module object or None if it could not be loaded.
    """
    sensors_path = Path(__file__).parent.parent / "sensors" / "main.py"
    if not sensors_path.exists():
        logger.warning("Sensors plugin not found at %s", sensors_path)
        return None

    spec = importlib.util.spec_from_file_location("plugin_sensors", sensors_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


# Cache the imported sensors module to avoid reloading on every API call
_SENSORS_MODULE = _get_sensor_module()


def get_sensor_data():
    """Proxy to sensors.get_sensor_data if available, otherwise return empty."""
    if _SENSORS_MODULE and hasattr(_SENSORS_MODULE, "get_sensor_data"):
        try:
            return _SENSORS_MODULE.get_sensor_data()
        except Exception as exc:
            logger.error("Error fetching sensor data via sensors plugin: %s", exc)
    # Fallback empty values
    return {"temperature": None, "humidity": None, "cpu_temp": None}


def load_config():
    """Load plugin configuration file (config.json)."""
    cfg_path = Path(__file__).parent / "config.json"
    config = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
        except Exception as exc:
            logger.error("Failed to load calendar plugin config: %s", exc)
    return config


# Public API required by kiosk framework -------------------------------------------------

def init(config):
    """Called once at startup by the kiosk backend.

    We simply return current sensor data so that the initial page render can
    already contain values (optional).
    """
    data = get_sensor_data()
    return {"data": data}


def api_data():
    """Endpoint `/api/plugins/calendar/data` - returns latest sensor data."""
    return get_sensor_data() 