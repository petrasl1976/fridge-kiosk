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
import google.oauth2.credentials
import google_auth_oauthlib.flow
import urllib.parse
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Allow OAuth2 over HTTP for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Add parent directory to sys.path to make imports work after moving to backend/
parent_dir = Path(__file__).resolve().parent
sys.path.append(str(parent_dir))
from backend.utils.config import load_config, get_plugin_path, get_env, setup_logging

# Initialize Jinja2 template environment
template_loader = jinja2.FileSystemLoader(searchpath=str(parent_dir / "backend/templates"))
template_env = jinja2.Environment(loader=template_loader)

# Add custom filters
def datetime_fromtimestamp(timestamp):
    """Convert Unix timestamp to datetime object"""
    return datetime.datetime.fromtimestamp(timestamp)

def strftime(dt, format_str):
    """Format datetime object using strftime"""
    return dt.strftime(format_str)

template_env.filters['datetime_fromtimestamp'] = datetime_fromtimestamp
template_env.filters['strftime'] = strftime

# Google OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/photoslibrary.readonly'
]

def credentials_to_dict(credentials):
    """Convert Google Credentials object to a dictionary."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_credentials():
    """Get valid credentials from token.json or return None."""
    token_path = Path(parent_dir / 'config' / 'token.json')
    if token_path.exists():
        try:
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                logger.debug("Successfully loaded token.json")
                return google.oauth2.credentials.Credentials(**token_data)
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            logger.debug(f"Token file path: {token_path}")
    else:
        logger.warning(f"token.json not found at {token_path}")
    return None

class KioskHTTPRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler for the kiosk"""
    
    def __init__(self, *args, config=None, plugins=None, **kwargs):
        self.config = config or {}
        self.plugins = plugins or {}
        self.root_dir = parent_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override the default logging to respect our logging configuration"""
        # Only log if logging is not OFF
        system_log_level = self.config.get('system', {}).get('logging', 'INFO').upper()
        if system_log_level != 'OFF':
            logger.info("%s - %s",
                        self.address_string(),
                        format % args)
    
    def log_error(self, format, *args):
        """Override error logging to respect our logging configuration"""
        # Only log if logging is not OFF
        system_log_level = self.config.get('system', {}).get('logging', 'INFO').upper()
        if system_log_level != 'OFF':
            logger.error("%s - %s",
                        self.address_string(),
                        format % args)
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            # Parse URL path and query parameters
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query = parse_qs(parsed_path.query)
            
            logger.debug(f"Received GET request: {path} with query params: {query}")

            # OAuth routes
            if path == '/authorize':
                logger.info("Handling OAuth authorization request")
                self.handle_authorize()
                return
            elif path == '/oauth2callback':
                logger.info("Handling OAuth callback")
                self.handle_oauth2callback()
                return

            # Route for the main page
            if path == '/' or path == '/index.html':
                logger.info("Serving main page")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                # Check if token exists
                token_path = Path(parent_dir / 'config' / 'token.json')
                self.config['token_exists'] = token_path.exists()
                logger.debug(f"Token exists: {self.config['token_exists']}")
                
                # Render the template
                try:
                    template = template_env.get_template('index.html')
                    html = template.render(
                        config=self.config,
                        plugins=self.plugins
                    )
                    self.wfile.write(html.encode('utf-8'))
                    logger.info("Main page rendered successfully")
                except Exception as e:
                    logger.error(f"Error rendering template: {e}")
                    logger.debug(f"Template error traceback: {traceback.format_exc()}")
                    self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
                
                return

            # Route for API endpoints
            if path.startswith('/api/'):
                parts = path.strip('/').split('/')
                if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'plugins':
                    plugin_name = parts[2]
                    endpoint = parts[3] if len(parts) > 3 else 'data'
                    
                    logger.info(f"Handling API request for plugin: {plugin_name}, endpoint: {endpoint}")
                    
                    # Look for the plugin module
                    try:
                        plugin_path = get_plugin_path(plugin_name)
                        main_py = plugin_path / 'main.py'
                        
                        if main_py.exists():
                            logger.debug(f"Found plugin module at: {main_py}")
                            # Import the plugin module
                            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", main_py)
                            plugin_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(plugin_module)
                            
                            # Find the API handler function
                            handler_name = f"api_{endpoint}"
                            if hasattr(plugin_module, handler_name):
                                logger.debug(f"Found handler: {handler_name}")
                                handler = getattr(plugin_module, handler_name)
                                result = handler()
                                
                                self.send_response(200)
                                self.send_header('Content-type', 'application/json')
                                self.end_headers()
                                self.wfile.write(json.dumps(result).encode('utf-8'))
                                logger.info(f"Successfully handled API request for {plugin_name}/{endpoint}")
                                return
                        
                        # If we get here, the handler wasn't found
                        logger.warning(f"Plugin API endpoint not found: {path}")
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            'error': f"Plugin API endpoint not found: {path}"
                        }).encode('utf-8'))
                        return
                    
                    except Exception as e:
                        logger.error(f"Error handling plugin API request: {e}")
                        logger.debug(f"API error traceback: {traceback.format_exc()}")
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
                logger.debug(f"Mapping path {path} to file: {file_path}")
                
                if not file_path.exists() or not file_path.is_file():
                    logger.warning(f"File not found: {path}")
                    self.send_response(404)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'File not found')
                    return
                
                # Get the file's MIME type
                mimetype, _ = mimetypes.guess_type(str(file_path))
                if mimetype is None:
                    mimetype = 'application/octet-stream'
                logger.debug(f"Serving file {file_path} with MIME type: {mimetype}")
                
                # Send the file
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                logger.info(f"Successfully served file: {path}")
                    
            except Exception as e:
                logger.error(f"Error serving file: {e}")
                logger.debug(f"File serving error traceback: {traceback.format_exc()}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Internal server error: {str(e)}".encode('utf-8'))

        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            logger.debug(f"Request handling error traceback: {traceback.format_exc()}")
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
                logger.debug(f"Mapping plugin resource: {path} -> {plugin_path / resource}")
                return plugin_path / resource
        
        # For static files (including favicon)
        if path.startswith('static/'):
            file_path = Path(self.root_dir) / 'backend' / path
            logger.debug(f"Mapping static file: {path} -> {file_path}")
            return file_path
        
        # For everything else, map to the templates directory
        file_path = Path(self.root_dir) / 'backend' / 'templates' / path
        logger.debug(f"Mapping template file: {path} -> {file_path}")
        return file_path
    
    def handle_authorize(self):
        """Handle /authorize route for Google OAuth."""
        client_secret_path = Path(parent_dir / 'config' / 'client_secret.json')
        if not client_secret_path.exists():
            self.send_error(500, "client_secret.json not found")
            return

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            str(client_secret_path), 
            scopes=SCOPES
        )
        flow.redirect_uri = f'http://localhost:{self.server.server_port}/oauth2callback'
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        # Store state in a temporary file since we don't have sessions
        with open(Path(parent_dir / 'config' / '.oauth_state'), 'w') as f:
            f.write(state)

        self.send_response(302)
        self.send_header('Location', authorization_url)
        self.end_headers()

    def handle_oauth2callback(self):
        """Handle /oauth2callback route for Google OAuth."""
        try:
            # Get state from temporary file
            state_path = Path(parent_dir / 'config' / '.oauth_state')
            if not state_path.exists():
                self.send_error(400, "No state found")
                return

            with open(state_path, 'r') as f:
                state = f.read().strip()
            state_path.unlink()  # Clean up

            client_secret_path = Path(parent_dir / 'config' / 'client_secret.json')
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                str(client_secret_path),
                scopes=SCOPES,
                state=state
            )
            flow.redirect_uri = f'http://localhost:{self.server.server_port}/oauth2callback'
            
            # Get authorization response URL
            authorization_response = f'http://localhost:{self.server.server_port}{self.path}'
            flow.fetch_token(authorization_response=authorization_response)
            
            credentials = flow.credentials
            if not credentials.refresh_token:
                self.send_error(400, "No refresh token received")
                return

            # Save credentials
            token_path = Path(parent_dir / 'config' / 'token.json')
            token_path.parent.mkdir(exist_ok=True)
            with open(token_path, 'w') as f:
                json.dump(credentials_to_dict(credentials), f)

            # --- RELOAD PLUGINS HERE ---
            self.server.plugins = load_plugins(self.config)
            logger.info("Plugins reloaded after OAuth2 callback.")
            # --- END RELOAD ---

            # Redirect to success page
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            self.send_error(500, str(e))


def load_plugins(config):
    """Load all enabled plugins"""
    plugins = {}
    enabled_plugins = config.get('enabledPlugins', [])
    
    # Get system-wide log level
    system_log_level = config.get('system', {}).get('logging', 'INFO').upper()
    if system_log_level == 'OFF':
        system_log_level = logging.CRITICAL + 1  # Effectively disables logging
    else:
        system_log_level = getattr(logging, system_log_level, logging.INFO)
    
    # Get orientation from system config for position selection
    orientation = config.get('system', {}).get('orientation', 'landscape')
    if system_log_level <= logging.CRITICAL:
        logger.info(f"System orientation: {orientation}")
        logger.info(f"Enabled plugins: {enabled_plugins}")
    
    # Loop through all enabled plugins
    for plugin_name in enabled_plugins:
        if system_log_level <= logging.CRITICAL:
            logger.info(f"Configuring: {plugin_name}")
        plugin_path = get_plugin_path(plugin_name)
        
        if not plugin_path.exists():
            if system_log_level <= logging.CRITICAL:
                logger.error(f"Plugin directory not found: {plugin_path}")
            continue
        
        # Load plugin's own config file
        plugin_config_path = plugin_path / 'config.json'
        plugin_config = {}
        
        if plugin_config_path.exists():
            try:
                with open(plugin_config_path, 'r') as f:
                    plugin_config = json.load(f)
                    # Report logging level
                    log_level = plugin_config.get('logging', 'INFO')
                    if system_log_level <= logging.CRITICAL:
                        logger.info(f"{plugin_name} - Logging level: {log_level}")
            except Exception as e:
                if system_log_level <= logging.CRITICAL:
                    logger.error(f"Error loading plugin config: {e}")
        
        # Ensure plugin has its own data directory
        plugin_data_dir = plugin_path / 'data'
        if not plugin_data_dir.exists():
            try:
                plugin_data_dir.mkdir(exist_ok=True)
                if system_log_level <= logging.CRITICAL:
                    logger.debug(f"Created data directory for plugin: {plugin_data_dir}")
            except Exception as e:
                if system_log_level <= logging.CRITICAL:
                    logger.error(f"Failed to create data directory for plugin {plugin_name}: {e}")
        
        # Get the position configuration based on orientation
        position = {}
        if 'position' in plugin_config:
            # If plugin has orientation-specific positions
            if orientation in plugin_config['position']:
                position = plugin_config['position'][orientation]
                if system_log_level <= logging.CRITICAL:
                    logger.info(f"{plugin_name} - Position: {position}")
            # If it has a general position setting
            elif isinstance(plugin_config['position'], dict) and not ('landscape' in plugin_config['position'] or 'portrait' in plugin_config['position']):
                position = plugin_config['position']
                if system_log_level <= logging.CRITICAL:
                    logger.info(f"{plugin_name} - Position: {position}")
            else:
                if system_log_level <= logging.CRITICAL:
                    logger.warning(f"Position config for {plugin_name} does not match expected format: {plugin_config['position']}")
        else:
            if system_log_level <= logging.CRITICAL:
                logger.warning(f"No position key found in config for plugin {plugin_name}")
        
        # Default fallback if no position found
        if not position:
            position = {
                'top': '0',
                'left': '0',
                'width': '100%',
                'height': '100%'
            }
            if system_log_level <= logging.CRITICAL:
                logger.warning(f"No position config found for plugin {plugin_name}, using defaults: {position}")
        
        # Set z_index based on plugin's position in the enabledPlugins array (starting from 1)
        position['z_index'] = enabled_plugins.index(plugin_name) + 1
        if system_log_level <= logging.CRITICAL:
            logger.info(f"{plugin_name} - z_index: {position['z_index']}")
        
        # Try to call init(config) if it exists
        plugin_data = {}
        main_py = plugin_path / 'main.py'
        if main_py.exists():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", main_py)
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                if hasattr(plugin_module, 'init'):
                    plugin_data = plugin_module.init(plugin_config).get('data', {})
            except Exception as e:
                if system_log_level <= logging.CRITICAL:
                    logger.error(f"Error calling init() for plugin {plugin_name}: {e}")

        plugin_info = {
            'name': plugin_name,
            'position': position,
            'view': None,
            'script': None,
            'style': None,
            'view_content': None,
            'data_dir': plugin_data_dir,
            'config': plugin_config,
            'data': plugin_data
        }
        
        # Check for basic files
        view_path = plugin_path / 'view.html'
        script_path = plugin_path / 'static' / 'script.js'
        style_path = plugin_path / 'static' / 'style.css'
        
        if view_path.exists():
            plugin_info['view'] = 'view.html'
            try:
                with open(view_path, 'r') as f:
                    view_template = template_env.from_string(f.read())
                    plugin_info['view_content'] = view_template.render(
                        config=config,
                        plugin=plugin_info
                    )
            except Exception as e:
                if system_log_level <= logging.CRITICAL:
                    logger.error(f"Error reading or rendering plugin view for '{plugin_name}': {e}")
                plugin_info['view_content'] = f"<div style='color:red;'>Error rendering {plugin_name} view: {e}</div>"
        
        if script_path.exists():
            plugin_info['script'] = 'static/script.js'
        
        if style_path.exists():
            plugin_info['style'] = 'static/style.css'
        
        plugins[plugin_name] = plugin_info
        if system_log_level <= logging.CRITICAL:
            logger.info(f"{plugin_name} - Loaded successfully")
    
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
    system_log_level = config.get('system', {}).get('logging', 'INFO').upper()
    if system_log_level == 'OFF':
        system_log_level = logging.CRITICAL + 1  # system_log_level=51  Effectively disables logging   
    else:
        system_log_level = getattr(logging, system_log_level, logging.INFO)
    
    # Set up logging with the configured level
    logger = setup_logging(config)
    logger.setLevel(system_log_level)
    
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
    
    # Only log if logging is not OFF
    if system_log_level <= logging.CRITICAL:
        logger.info(f"Server started on port {args.port}")
        logger.info(f"Open http://localhost:{args.port} in your browser")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if system_log_level <= logging.CRITICAL:
            logger.info("Server stopped by user")
        httpd.server_close()
        sys.exit(0)


if __name__ == "__main__":
    main() 