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
                    "orientation": "portrait",
                    "logging": "WARNING",
                    "fontFamily": "'Courier New', monospace"
                },
                "enabledPlugins": [ "date-time" ]
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

def get_plugin_log_level(plugin_name, config):
    """
    Get the log level for a specific plugin from its own config file.
    
    Args:
        plugin_name (str): The name of the plugin.
        config (dict): The main configuration dictionary.
        
    Returns:
        int: The logging level for the plugin.
    """
    # Get plugin's config file path
    plugin_path = get_plugin_path(plugin_name)
    plugin_config_path = plugin_path / 'config.json'
    
    try:
        if plugin_config_path.exists():
            with open(plugin_config_path, 'r') as f:
                plugin_config = json.load(f)
                if 'logging' in plugin_config:
                    level = plugin_config['logging'].upper()
                    if level == 'OFF':
                        return logging.CRITICAL + 1  # Effectively disables logging
                    return getattr(logging, level, logging.INFO)
    except Exception as e:
        logger.error(f"Error reading plugin config for {plugin_name}: {e}")
    
    # Fall back to system-wide log level
    return getattr(logging, config.get('system', {}).get('logging', 'INFO').upper(), logging.INFO)

def setup_logging(config=None):
    """Set up logging configuration for the entire application"""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Get system-wide log level from config or default to INFO
    system_log_level = config.get('system', {}).get('logging', 'INFO').upper()
    if system_log_level == 'OFF':
        system_log_level = logging.CRITICAL + 1  # Effectively disables logging
    else:
        system_log_level = getattr(logging, system_log_level, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(system_log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        'google_auth_httplib2', 'google.auth.transport.requests', 
        'requests', 'PIL', 'matplotlib'
    ]
    
    for logger_name in noisy_loggers:
        lgr = logging.getLogger(logger_name)
        lgr.setLevel(logging.WARNING)
        for handler in lgr.handlers[:]:
            lgr.removeHandler(handler)
        lgr.propagate = True
    
    # Configure plugin loggers
    if config and 'enabledPlugins' in config:
        for plugin_name in config['enabledPlugins']:
            plugin_logger = logging.getLogger(f'plugins.{plugin_name}')
            plugin_logger.setLevel(get_plugin_log_level(plugin_name, config))
            # Don't propagate to root logger to avoid duplicate messages
            plugin_logger.propagate = False
            # Add handlers to plugin logger
            plugin_logger.addHandler(file_handler)
            if os.environ.get('FLASK_ENV') == 'development':
                plugin_logger.addHandler(console_handler)
    
    # Log startup information
    root_logger.info("Logging system initialized")
    root_logger.info(f"System log level set to: {logging.getLevelName(system_log_level)}")
    root_logger.info(f"Log file: {logs_dir / 'fridge-kiosk.log'}")
    
    return root_logger 