#!/usr/bin/env python3
"""
Configuration utilities for the fridge-kiosk system.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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