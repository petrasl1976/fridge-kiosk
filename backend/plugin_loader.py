#!/usr/bin/env python3
import os
import sys
import json
import logging
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import List, Dict, Any, Optional, Callable

# Configure logger
logger = logging.getLogger(__name__)

class Plugin:
    """
    Represents a plugin in the system.
    """
    def __init__(self, name: str, module: ModuleType, enabled: bool = True, config: Dict = None):
        self.name = name
        self.module = module
        self.enabled = enabled
        self.config = config or {}
        
        # Check if required methods are implemented
        self.has_setup = hasattr(module, 'setup') and callable(module.setup)
        self.has_get_routes = hasattr(module, 'get_routes') and callable(module.get_routes)
        self.has_get_data = hasattr(module, 'get_data') and callable(module.get_data)
        self.has_cleanup = hasattr(module, 'cleanup') and callable(module.cleanup)
        
        # Check for template and static files
        self.template_file = None
        self.static_dir = None
        
    def setup(self, app):
        """Call the plugin's setup method if it exists."""
        if self.has_setup:
            try:
                self.module.setup(app)
                logger.debug(f"Plugin {self.name} setup completed")
                return True
            except Exception as e:
                logger.error(f"Error in plugin {self.name} setup: {e}")
                return False
        return None
    
    def get_routes(self, app):
        """Get the plugin's routes if the method exists."""
        if self.has_get_routes:
            try:
                return self.module.get_routes(app)
            except Exception as e:
                logger.error(f"Error getting routes for plugin {self.name}: {e}")
        return []
    
    def get_data(self):
        """Get the plugin's data if the method exists."""
        if self.has_get_data:
            try:
                return self.module.get_data()
            except Exception as e:
                logger.error(f"Error getting data from plugin {self.name}: {e}")
        return {}
    
    def cleanup(self):
        """Call the plugin's cleanup method if it exists."""
        if self.has_cleanup:
            try:
                self.module.cleanup()
                logger.debug(f"Plugin {self.name} cleanup completed")
                return True
            except Exception as e:
                logger.error(f"Error in plugin {self.name} cleanup: {e}")
                return False
        return None

def load_plugin_module(plugin_name: str, plugin_dir: str) -> Optional[ModuleType]:
    """
    Load a plugin module from the given directory.
    
    Args:
        plugin_name: The name of the plugin
        plugin_dir: The directory containing the plugin
        
    Returns:
        The loaded module if successful, None otherwise
    """
    try:
        # Check if __init__.py exists
        init_file = os.path.join(plugin_dir, '__init__.py')
        if not os.path.isfile(init_file):
            logger.warning(f"Plugin {plugin_name} missing __init__.py file")
            return None
        
        # Import the module
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", init_file)
        if not spec:
            logger.error(f"Failed to create module spec for {plugin_name}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"plugins.{plugin_name}"] = module
        spec.loader.exec_module(module)
        
        # Check if module has required attributes
        if not hasattr(module, 'PLUGIN_NAME'):
            logger.warning(f"Plugin {plugin_name} is missing PLUGIN_NAME attribute")
            module.PLUGIN_NAME = plugin_name
            
        if not hasattr(module, 'PLUGIN_VERSION'):
            logger.warning(f"Plugin {plugin_name} is missing PLUGIN_VERSION attribute")
            module.PLUGIN_VERSION = "0.1.0"
            
        if not hasattr(module, 'PLUGIN_DESCRIPTION'):
            logger.warning(f"Plugin {plugin_name} is missing PLUGIN_DESCRIPTION attribute")
            module.PLUGIN_DESCRIPTION = "No description provided"
        
        return module
        
    except Exception as e:
        logger.error(f"Failed to load plugin {plugin_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def load_plugins(app) -> List[Plugin]:
    """
    Load and initialize all enabled plugins from the plugins directory.
    
    Args:
        app: The Flask application object
        
    Returns:
        A list of loaded Plugin objects
    """
    plugins = []
    plugins_dir = app.config['PLUGINS_DIR']
    main_config = app.config['MAIN_CONFIG']
    
    logger.info(f"Loading plugins from {plugins_dir}")
    
    # Get enabled plugins from config
    enabled_plugins = {}
    for plugin_info in main_config.get('plugins', []):
        if plugin_info.get('enabled', False):
            plugin_name = plugin_info.get('name')
            if plugin_name:
                enabled_plugins[plugin_name] = plugin_info.get('config', {})
    
    # Check each directory in the plugins directory
    for item in os.listdir(plugins_dir):
        plugin_dir = os.path.join(plugins_dir, item)
        
        # Skip if not a directory or hidden
        if not os.path.isdir(plugin_dir) or item.startswith('.'):
            continue
            
        # Check if plugin is enabled in config
        if item not in enabled_plugins:
            logger.info(f"Plugin {item} found but not enabled in config, skipping")
            continue
        
        logger.info(f"Loading plugin: {item}")
        
        # Load the plugin module
        module = load_plugin_module(item, plugin_dir)
        if not module:
            logger.error(f"Failed to load plugin module: {item}")
            continue
        
        # Create plugin object
        plugin = Plugin(
            name=item,
            module=module,
            enabled=True,
            config=enabled_plugins.get(item, {})
        )
        
        # Set up the plugin
        setup_result = plugin.setup(app)
        if setup_result is False:  # Setup explicitly failed
            logger.error(f"Plugin {item} setup failed, skipping")
            continue
            
        plugins.append(plugin)
        logger.info(f"Plugin {item} loaded successfully")
    
    return plugins

def get_plugin_routes(app, plugins: List[Plugin]):
    """
    Register all routes from the loaded plugins.
    
    Args:
        app: The Flask application object
        plugins: List of loaded Plugin objects
    """
    for plugin in plugins:
        if not plugin.enabled:
            continue
            
        logger.debug(f"Getting routes for plugin: {plugin.name}")
        routes = plugin.get_routes(app)
        
        if routes:
            logger.info(f"Registered {len(routes)} routes for plugin {plugin.name}")

def get_plugin_data(plugins: List[Plugin]) -> Dict[str, Any]:
    """
    Get data from all plugins to be rendered in the templates.
    
    Args:
        plugins: List of loaded Plugin objects
        
    Returns:
        Dictionary with plugin data keyed by plugin name
    """
    data = {}
    for plugin in plugins:
        if not plugin.enabled:
            continue
            
        logger.debug(f"Getting data from plugin: {plugin.name}")
        plugin_data = plugin.get_data()
        
        if plugin_data:
            data[plugin.name] = plugin_data
    
    return data

def cleanup_plugins(plugins: List[Plugin]):
    """
    Clean up all loaded plugins.
    
    Args:
        plugins: List of loaded Plugin objects
    """
    for plugin in plugins:
        if not plugin.enabled:
            continue
            
        logger.debug(f"Cleaning up plugin: {plugin.name}")
        plugin.cleanup() 