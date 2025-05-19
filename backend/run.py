#!/home/kiosk/fridge-kiosk/venv/bin/python3
"""
Fridge Kiosk - Main Backend Application
Launches a simple HTTP server and manages plugins
"""

import os
import sys
import json
import logging
import argparse
import importlib.util
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import mimetypes
import jinja2
import traceback
import datetime

# Add parent directory to sys.path to make imports work after moving to backend/
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from backend.utils.config import load_config, get_plugin_path, get_env

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, 'logs/backend.log'))
    ]
)
logger = logging.getLogger('fridge-kiosk')

# Initialize Jinja2 template environment
template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(parent_dir, "backend/templates"))
template_env = jinja2.Environment(loader=template_loader)

# Add custom filters
def datetime_fromtimestamp(timestamp):
    """Convert Unix timestamp to datetime object"""
    return datetime.datetime.fromtimestamp(timestamp)

template_env.filters['datetime_fromtimestamp'] = datetime_fromtimestamp

class KioskHTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler for the kiosk"""
    
    def __init__(self, *args, config=None, plugins=None, **kwargs):
        self.config = config or {}
        self.plugins = plugins or {}
        self.root_dir = parent_dir
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        # Parse the URL
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Route for the main page
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Render the template
            try:
                template = template_env.get_template('index.html')
                html = template.render(
                    config=self.config,
                    plugins=self.plugins
                )
                self.wfile.write(html.encode('utf-8'))
            except Exception as e:
                logger.error(f"Error rendering template: {e}")
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
            
            return
        
        # Route for API endpoints
        if path.startswith('/api/'):
            parts = path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'plugins':
                plugin_name = parts[2]
                endpoint = parts[3] if len(parts) > 3 else 'data'
                
                # Look for the plugin module
                try:
                    plugin_path = get_plugin_path(plugin_name)
                    main_py = plugin_path / 'main.py'
                    
                    if main_py.exists():
                        # Import the plugin module
                        spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", main_py)
                        plugin_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(plugin_module)
                        
                        # Find the API handler function
                        handler_name = f"api_{endpoint}"
                        if hasattr(plugin_module, handler_name):
                            handler = getattr(plugin_module, handler_name)
                            result = handler()
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(result).encode('utf-8'))
                            return
                    
                    # If we get here, the handler wasn't found
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': f"Plugin API endpoint not found: {path}"
                    }).encode('utf-8'))
                    return
                
                except Exception as e:
                    logger.error(f"Error handling plugin API request: {e}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': str(e)
                    }).encode('utf-8'))
                    return
        
        # For other static files
        try:
            # Map URL path to file system path
            file_path = self.map_path_to_file(path)
            
            if not file_path.exists() or not file_path.is_file():
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return
            
            # Get the file's MIME type
            mimetype, _ = mimetypes.guess_type(str(file_path))
            if mimetype is None:
                mimetype = 'application/octet-stream'
            
            # Send the file
            self.send_response(200)
            self.send_header('Content-type', mimetype)
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            logger.error(f"Error serving file: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Internal server error: {str(e)}".encode('utf-8'))
    
    def map_path_to_file(self, path):
        """Map URL path to file system path"""
        # Clean up the path
        path = path.lstrip('/')
        
        # Check if this is a plugin resource
        if path.startswith('plugins/'):
            parts = path.split('/')
            if len(parts) >= 3:
                plugin_name = parts[1]
                resource = '/'.join(parts[2:])
                plugin_path = get_plugin_path(plugin_name)
                return plugin_path / resource
        
        # For everything else, map to the templates directory
        return Path(self.root_dir) / 'backend' / 'templates' / path
    
    def log_message(self, format, *args):
        """Log messages to our logger instead of stderr"""
        logger.info("%s - %s",
                    self.address_string(),
                    format % args)


def load_plugins(config):
    """Load all enabled plugins"""
    plugins = {}
    enabled_plugins = config.get('enabledPlugins', [])
    
    # Get orientation from system config for position selection
    orientation = config.get('system', {}).get('orientation', 'landscape')
    logger.info(f"System orientation: {orientation}")
    
    logger.info(f"Loading {len(enabled_plugins)} enabled plugins")
    
    # Loop through all enabled plugins
    for plugin_index, plugin_name in enumerate(enabled_plugins):
        logger.info(f"Loading plugin: {plugin_name}")
        plugin_path = get_plugin_path(plugin_name)
        
        if not os.path.exists(plugin_path):
            logger.error(f"Plugin directory not found: {plugin_path}")
            continue
        
        # Load plugin's own config file
        plugin_config_path = os.path.join(plugin_path, 'config.json')
        plugin_config = {}
        
        if os.path.exists(plugin_config_path):
            try:
                with open(plugin_config_path, 'r') as f:
                    plugin_config = json.load(f)
                logger.info(f"Loaded configuration for plugin {plugin_name}: {plugin_config_path}")
            except Exception as e:
                logger.error(f"Error loading plugin config: {e}")
        else:
            logger.warning(f"Plugin config not found: {plugin_config_path}")
        
        # Ensure plugin has its own data directory
        plugin_data_dir = os.path.join(plugin_path, 'data')
        if not os.path.exists(plugin_data_dir):
            try:
                os.makedirs(plugin_data_dir, exist_ok=True)
                logger.debug(f"Created data directory for plugin: {plugin_data_dir}")
            except Exception as e:
                logger.error(f"Failed to create data directory for plugin {plugin_name}: {e}")
        
        # Get the position configuration based on orientation
        position = {}
        if 'position' in plugin_config:
            # If plugin has orientation-specific positions
            if orientation in plugin_config['position']:
                position = plugin_config['position'][orientation]
                logger.info(f"Using {orientation} position for plugin {plugin_name}: {position}")
            # If it has a general position setting
            elif isinstance(plugin_config['position'], dict) and not ('landscape' in plugin_config['position'] or 'portrait' in plugin_config['position']):
                position = plugin_config['position']
                logger.info(f"Using default position for plugin {plugin_name}: {position}")
        
        # Default fallback if no position found
        if not position:
            position = {
                'top': '0',
                'left': '0',
                'width': '100%',
                'height': '100%'
            }
            logger.warning(f"No position config found for plugin {plugin_name}, using defaults: {position}")
        
        # Set z_index based on plugin's position in the enabledPlugins array (starting from 1)
        position['z_index'] = plugin_index + 1
        logger.info(f"Set z_index={position['z_index']} for plugin {plugin_name} based on its position in enabledPlugins")
        
        # Default plugin info
        plugin_info = {
            'name': plugin_name,
            'position': position,
            'view': None,
            'script': None,
            'style': None,
            'view_content': None,
            'data_dir': plugin_data_dir,
            'config': plugin_config,
            'data': {}  # Tik placeholder, nebe fetchinam realių duomenų čia
        }
        
        # Check for basic files
        view_path = os.path.join(plugin_path, 'view.html')
        script_path = os.path.join(plugin_path, 'static', 'script.js')
        style_path = os.path.join(plugin_path, 'static', 'style.css')
        
        if os.path.exists(view_path):
            plugin_info['view'] = 'view.html'
            try:
                with open(view_path, 'r') as f:
                    view_template = template_env.from_string(f.read())
                    plugin_info['view_content'] = view_template.render(
                        config=config,
                        plugin=plugin_info
                    )
            except Exception as e:
                logger.error(f"Error reading or rendering plugin view for '{plugin_name}': {e}\n{traceback.format_exc()}")
                plugin_info['view_content'] = f"<div style='color:red;'>Error rendering {plugin_name} view: {e}</div>"
        
        if os.path.exists(script_path):
            plugin_info['script'] = 'static/script.js'
        
        if os.path.exists(style_path):
            plugin_info['style'] = 'static/style.css'
        
        plugins[plugin_name] = plugin_info
    
    return plugins


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fridge Kiosk Application')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port to run the HTTP server on')
    parser.add_argument('-c', '--config', type=str, default='config/main.json', help='Path to configuration file')
    return parser.parse_args()


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Load configuration
    config = load_config()
    
    # Configure logging level from config
    if 'logLevel' in config.get('system', {}):
        log_level = getattr(logging, config['system']['logLevel'].upper(), logging.INFO)
        logger.setLevel(log_level)
    
    # Load plugins
    plugins = load_plugins(config)
    
    # Create handler factory with app config
    def handler(*args, **kwargs):
        return KioskHTTPRequestHandler(
            *args,
            config=config,
            plugins=plugins,
            **kwargs
        )
    
    # Start HTTP server
    server_address = ('', args.port)
    httpd = HTTPServer(server_address, handler)
    
    logger.info(f"Starting server on port {args.port}")
    logger.info(f"Open http://localhost:{args.port} in your browser")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down the server")
        httpd.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main() 