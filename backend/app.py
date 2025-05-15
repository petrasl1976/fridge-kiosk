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
    orientation = config.get('system', {}).get('display_orientation', 'landscape')
    theme = config.get('system', {}).get('theme', 'dark')
    font_family = config.get('system', {}).get('font_family', 'sans-serif')
    
    # Get data from all plugins
    plugin_data = get_plugin_data(plugins)
    
    # Get plugin config for frontend
    frontend_config = {
        'system': config.get('system', {}),
        'plugins': []
    }
    
    # Add enabled plugins with their frontend configuration
    for plugin_info in config.get('plugins', []):
        if plugin_info.get('enabled', False):
            plugin_name = plugin_info.get('name')
            plugin_config = plugin_info.get('config', {})
            
            # Position based on orientation
            position = plugin_config.get('position', {}).get(orientation, {})
            
            frontend_config['plugins'].append({
                'name': plugin_name,
                'config': plugin_config,
                'position': position
            })
    
    return render_template('index.html', 
                          config=frontend_config,
                          plugin_data=plugin_data,
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