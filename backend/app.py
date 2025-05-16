#!/usr/bin/env python3
import os
import sys
import json
import logging
import datetime
import importlib
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

# Add parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Local imports
from backend.utils.config import load_config
from backend.plugin_loader import load_plugins, get_plugin_routes, get_plugin_data

# Load environment variables from .env file
env_path = os.path.join(parent_dir, 'config', '.env')
load_dotenv(dotenv_path=env_path)

# Configure logging
log_dir = os.path.join(parent_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'backend.log')

logging.basicConfig(
    level=logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            template_folder=os.path.join(parent_dir, 'frontend'),
            static_folder=os.path.join(parent_dir, 'frontend'),
            static_url_path='')

# Load configuration
config = load_config()
app.config['MAIN_CONFIG'] = config
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_key')

# Set plugin directories
plugins_dir = os.path.join(parent_dir, 'plugins')
app.config['PLUGINS_DIR'] = plugins_dir

# Load plugins
plugins = load_plugins(app)
logger.info(f"Loaded {len(plugins)} plugins")

# Register plugin-specific routes
get_plugin_routes(app, plugins)

@app.route('/')
def index():
    """Render the main index page with all enabled plugins."""
    system_config = config.get('system', {})
    orientation = system_config.get('orientation', 'landscape')
    theme = system_config.get('theme', 'dark')
    font_family = system_config.get('fontFamily', 'sans-serif')
    
    # Get data from all plugins
    plugin_data = get_plugin_data(plugins)
    
    # Get plugin list with their frontend configuration
    frontend_plugins = []
    
    # Add plugin data for each loaded plugin
    for plugin in plugins:
        # Position settings based on current orientation
        positions = plugin.config.get('position', {})
        position = {}
        
        if orientation == 'portrait' and 'portrait' in positions:
            position = positions.get('portrait', {})
        elif orientation == 'landscape' and 'landscape' in positions:
            position = positions.get('landscape', {})
        elif not isinstance(positions, dict):
            position = {}
        else:
            # Fallback to direct position if no orientation-specific settings
            position = positions
        
        # Add plugin info
        frontend_plugins.append({
            'name': plugin.name,
            'displayName': plugin.config.get('displayName', plugin.name.capitalize()),
            'position': position,
            'view_content': plugin_data.get(plugin.name, {}).get('view_content', '')
        })
    
    # Combine all config data for frontend
    frontend_config = {
        'system': system_config,
        'plugins': {}
    }
    
    # Add plugin configs to the frontend config
    for plugin in plugins:
        frontend_config['plugins'][plugin.name] = plugin.config
    
    return render_template('index.html', 
                          config=frontend_config,
                          plugins=frontend_plugins,
                          plugins_data=plugin_data,
                          orientation=orientation,
                          theme=theme,
                          font_family=font_family)

@app.route('/api/system/status', methods=['GET'])
def system_status():
    """Return system status information."""
    status = {
        'time': datetime.datetime.now().isoformat(),
        'plugins': [p.name for p in plugins],
        'version': '1.0.0',
        'uptime': get_uptime()
    }
    return jsonify(status)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Return the current system configuration."""
    # Filter out sensitive information
    safe_config = config.copy()
    return jsonify(safe_config)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return jsonify(error=str(e)), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    return jsonify(error="Internal server error"), 500

def get_uptime():
    """Get system uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        
        # Format uptime nicely
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{int(days)}d "
        if hours > 0 or days > 0:
            uptime_str += f"{int(hours)}h "
        if minutes > 0 or hours > 0 or days > 0:
            uptime_str += f"{int(minutes)}m "
        uptime_str += f"{int(seconds)}s"
        
        return uptime_str
    except:
        return "Unknown"

if __name__ == '__main__':
    debug_mode = config.get('system', {}).get('debug', False)
    port = int(os.getenv('PORT', 8080))
    
    # Log startup information
    logger.info(f"Starting Fridge Kiosk backend on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1) 