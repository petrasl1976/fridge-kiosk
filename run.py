#!/usr/bin/env python3
"""
Fridge Kiosk - Main Application
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
from backend.utils.config import load_config, get_plugin_path, get_env

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('kiosk.log')
    ]
)
logger = logging.getLogger('fridge-kiosk')

# Initialize Jinja2 template environment
template_loader = jinja2.FileSystemLoader(searchpath="./frontend")
template_env = jinja2.Environment(loader=template_loader)

class KioskHTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler for the kiosk"""
    
    def __init__(self, *args, config=None, plugins=None, plugins_data=None, **kwargs):
        self.config = config or {}
        self.plugins = plugins or []
        self.plugins_data = plugins_data or {}
        self.root_dir = str(Path(__file__).parent)
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
                    plugins=self.plugins,
                    plugins_data=self.plugins_data
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
        
        # For everything else, map to the frontend directory
        return Path(self.root_dir) / 'frontend' / path
    
    def log_message(self, format, *args):
        """Log messages to our logger instead of stderr"""
        logger.info("%s - - [%s] %s",
                    self.address_string(),
                    self.log_date_time_string(),
                    format % args)


def load_plugins(config):
    """Load all enabled plugins"""
    plugins = []
    plugins_data = {}
    enabled_plugins = config.get('enabledPlugins', [])
    
    logger.info(f"Loading {len(enabled_plugins)} enabled plugins")
    
    for plugin_name in enabled_plugins:
        logger.info(f"Loading plugin: {plugin_name}")
        plugin_path = get_plugin_path(plugin_name)
        
        if not os.path.exists(plugin_path):
            logger.error(f"Plugin directory not found: {plugin_path}")
            continue
        
        # Get plugin configuration
        plugin_config = config.get('plugins', {}).get(plugin_name, {})
        
        # Default plugin info
        plugin_info = {
            'name': plugin_name,
            'position': plugin_config.get('position', {
                'top': '0',
                'left': '0',
                'width': '100%',
                'height': '100%',
                'z_index': 1
            }),
            'view': None,
            'script': None,
            'style': None,
            'view_content': None
        }
        
        # Check for basic files
        view_path = os.path.join(plugin_path, 'view.html')
        script_path = os.path.join(plugin_path, 'static', 'script.js')
        style_path = os.path.join(plugin_path, 'static', 'style.css')
        
        if os.path.exists(view_path):
            plugin_info['view'] = 'view.html'
            try:
                with open(view_path, 'r') as f:
                    plugin_info['view_content'] = f.read()
            except Exception as e:
                logger.error(f"Error reading plugin view: {e}")
        
        if os.path.exists(script_path):
            plugin_info['script'] = 'static/script.js'
        
        if os.path.exists(style_path):
            plugin_info['style'] = 'static/style.css'
        
        # Check for plugin main.py
        plugin_main = os.path.join(plugin_path, 'main.py')
        if os.path.exists(plugin_main):
            try:
                # Import the plugin module
                spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", plugin_main)
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                
                # Initialize the plugin if it has an init function
                if hasattr(plugin_module, 'init'):
                    plugin_data = plugin_module.init(plugin_config)
                    plugins_data[plugin_name] = plugin_data
                    logger.info(f"Plugin {plugin_name} initialized successfully")
                else:
                    logger.warning(f"Plugin {plugin_name} has no init function")
                    plugins_data[plugin_name] = {}
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
                plugins_data[plugin_name] = {'error': str(e)}
        
        plugins.append(plugin_info)
    
    return plugins, plugins_data


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Fridge Kiosk Application')
    parser.add_argument('-p', '--port', type=int, default=8000, help='Port to run the HTTP server on')
    parser.add_argument('-c', '--config', type=str, default='config/main.json', help='Path to configuration file')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()


def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging level based on arguments
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Load configuration
    config = load_config()
    
    # Configure logging level from config if not in debug mode
    if not args.debug and 'logLevel' in config.get('system', {}):
        log_level = getattr(logging, config['system']['logLevel'].upper(), logging.INFO)
        logger.setLevel(log_level)
    
    # Load plugins
    plugins, plugins_data = load_plugins(config)
    
    # Create handler factory with app config
    def handler(*args, **kwargs):
        return KioskHTTPRequestHandler(
            *args,
            config=config,
            plugins=plugins,
            plugins_data=plugins_data,
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