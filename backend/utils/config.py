#!/usr/bin/env python3
"""
Configuration utilities for the fridge-kiosk system.
"""

import os
import json
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sys

logger = logging.getLogger(__name__)

class PluginFormatter(logging.Formatter):
    """Custom formatter that adds plugin name and improves readability"""
    def format(self, record):
        # Get plugin name from path
        folder = os.path.basename(os.path.dirname(record.pathname))
        prefix = f"[{folder}] "
        
        # Add color for different log levels
        if record.levelno >= logging.ERROR:
            prefix = f"\033[91m{prefix}"  # Red for errors
        elif record.levelno >= logging.WARNING:
            prefix = f"\033[93m{prefix}"  # Yellow for warnings
        elif record.levelno >= logging.INFO:
            prefix = f"\033[92m{prefix}"  # Green for info
        else:
            prefix = f"\033[94m{prefix}"  # Blue for debug
            
        record.msg = prefix + str(record.msg)
        return super().format(record)

def load_config():
    """
    Load the main configuration file.
    
    Returns:
        dict: The configuration dictionary, or empty dict if not found.
    """
    # Get the project root directory (parent of the backend directory)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Path to the config file
    config_path = os.path.join(project_root, 'config', 'main.json')
    
    try:
        if os.path.exists(config_path):
            logger.info(f"Loading configuration from {config_path}")
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        else:
            logger.warning(f"Configuration file not found: {config_path}")
            # Return default configuration
            return {
                "system": {
                    "name": "Fridge Kiosk",
                    "theme": "dark",
                    "orientation": "landscape",
                    "fontFamily": "Courier New, monospace",
                    "logLevel": "info"
                },
                "enabledPlugins": ["sensors", "date-time"]
            }
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def get_env(key, default=None):
    """
    Get an environment variable with a default value.
    
    Args:
        key (str): The environment variable name.
        default: The default value if not found.
        
    Returns:
        The environment variable value, or the default if not found.
    """
    return os.environ.get(key, default)

def get_plugin_path(plugin_name):
    """
    Get the absolute path to a plugin directory.
    
    Args:
        plugin_name (str): The name of the plugin.
        
    Returns:
        str: The absolute path to the plugin directory.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return Path(os.path.join(project_root, 'plugins', plugin_name))

def list_plugins():
    """
    List all available plugins in the plugins directory.
    
    Returns:
        list: A list of plugin names.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    plugins_dir = os.path.join(project_root, 'plugins')
    
    if not os.path.exists(plugins_dir):
        logger.warning(f"Plugins directory not found: {plugins_dir}")
        return []
    
    # Get all directories in the plugins directory
    return [d for d in os.listdir(plugins_dir) 
            if os.path.isdir(os.path.join(plugins_dir, d)) and not d.startswith('_')]

def get_plugin_config(plugin_name):
    """
    Get the configuration for a specific plugin.
    
    Args:
        plugin_name (str): The name of the plugin.
        
    Returns:
        dict: The plugin configuration, or empty dict if not found.
    """
    config = load_config()
    return config.get('plugins', {}).get(plugin_name, {}) 

def setup_logging(config=None):
    """Set up logging configuration for the entire application"""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Get log level from config or default to INFO
    log_level = getattr(logging, config.get('system', {}).get('logLevel', 'INFO').upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = PluginFormatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add rotating file handler
    file_handler = RotatingFileHandler(
        logs_dir / 'fridge-kiosk.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Add console handler for development
    if os.environ.get('FLASK_ENV') == 'development':
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Set specific loggers to WARNING and remove their handlers
    noisy_loggers = [
        'werkzeug', 'googleapiclient', 'urllib3', 'discord', 
        'google_calendar', 'google_calendar_summary',
        'google_auth_httplib2', 'google.auth.transport.requests', 
        'requests', 'PIL', 'matplotlib'
    ]
    
    for logger_name in noisy_loggers:
        lgr = logging.getLogger(logger_name)
        lgr.setLevel(logging.WARNING)
        for handler in lgr.handlers[:]:
            lgr.removeHandler(handler)
        lgr.propagate = True
    
    # Log startup information
    root_logger.info("Logging system initialized")
    root_logger.info(f"Log level set to: {logging.getLevelName(log_level)}")
    root_logger.info(f"Log file: {logs_dir / 'fridge-kiosk.log'}")
    
    return root_logger 