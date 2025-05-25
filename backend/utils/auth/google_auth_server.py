#!/usr/bin/env python3
"""
OAuth authentication server for Google services.
This server handles the OAuth flow and stores the credentials.
It can be used for Google Calendar, Google Photos, and other Google services.
"""

import os
import json
import logging
from pathlib import Path
import requests
from flask import Flask, render_template, redirect, url_for, session, request

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('google-auth-server')

# Get the project root directory
current_dir = Path(__file__).resolve().parent
PROJECT_ROOT = current_dir.parent.parent.parent
CLIENT_SECRET_FILE = PROJECT_ROOT / 'config' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'config' / 'token.json'

# For development only
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Create Flask app
app = Flask(__name__, template_folder=str(current_dir / "templates"))
app.secret_key = os.urandom(24)

# Default OAuth scopes (can be customized when running the server)
SCOPES = [
    'https://www.googleapis.com/auth/photoslibrary.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
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

@app.route('/')
def index():
    """Main page that checks authentication status and provides links"""
    # Get the service name from query parameters or use default
    service_name = request.args.get('service', 'Google API')
    
    # Check if we have stored credentials
    token_exists = TOKEN_FILE.exists()
    client_secret_exists = CLIENT_SECRET_FILE.exists()
    
    context = {
        'token_exists': token_exists,
        'client_secret_exists': client_secret_exists,
        'service_name': service_name,
        'resource_id': os.getenv("GOOGLE_RESOURCE_ID", "primary")
    }
    
    # If we have token.json, try to verify it works
    if token_exists:
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            creds = google.oauth2.credentials.Credentials(**token_data)
            
            # Check if expired but can be refreshed
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                
                # Save refreshed credentials
                with open(TOKEN_FILE, 'w') as f:
                    token_data = credentials_to_dict(creds)
                    json.dump(token_data, f)
                
                context['token_refreshed'] = True
            
            context['authenticated'] = True
            
        except Exception as e:
            logger.error(f"Error verifying credentials: {e}")
            context['error'] = str(e)
            context['authenticated'] = False
    
    return render_template('auth_index.html', **context)

@app.route('/authorize')
def authorize():
    """Start OAuth flow"""
    if not CLIENT_SECRET_FILE.exists():
        return "Error: client_secret.json not found in config directory"
    
    # Naudok abu scope
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES
    )
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback from Google"""
    state = session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    if not credentials.refresh_token:
        return "Error: No refresh token received. Please revoke access and try again."
    token_data = credentials_to_dict(credentials)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)
    session['credentials'] = token_data
    return redirect(url_for('success'))

@app.route('/success')
def success():
    """Show success page after authentication"""
    service = session.get('service', 'Google service')
    return render_template('auth_success.html', service_name=service)

@app.route('/revoke')
def revoke():
    """Revoke current credentials and delete token.json"""
    if not TOKEN_FILE.exists():
        return "No token.json found"
    
    try:
        # Load credentials
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        credentials = google.oauth2.credentials.Credentials(**token_data)
        
        # Make revoke request
        revoke = requests.post(
            'https://oauth2.googleapis.com/revoke',
            params={'token': credentials.token},
            headers={'content-type': 'application/x-www-form-urlencoded'}
        )
        
        # Delete token.json
        os.remove(TOKEN_FILE)
        
        return "Credentials revoked and token.json deleted"
    except Exception as e:
        return f"Error: {str(e)}"

def create_template_files():
    """Create template files if they don't exist"""
    template_dir = current_dir / "templates"
    template_dir.mkdir(exist_ok=True)
    
    auth_index_path = template_dir / "auth_index.html"
    if not auth_index_path.exists():
        with open(auth_index_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Google Authentication</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: #f5f5f5; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .success { color: green; }
        .error { color: red; }
        .button { display: inline-block; background: #4285f4; color: white; padding: 10px 20px; 
                 text-decoration: none; border-radius: 4px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ service_name }} Authentication</h1>
        
        <div class="card">
            <h2>Configuration Status</h2>
            <p><strong>client_secret.json:</strong> {% if client_secret_exists %}✅ Found{% else %}❌ Missing{% endif %}</p>
            <p><strong>token.json:</strong> {% if token_exists %}✅ Found{% else %}❌ Missing{% endif %}</p>
            <p><strong>Resource ID:</strong> {{ resource_id }}</p>
            
            {% if authenticated %}
                <p class="success">✅ Successfully authenticated with {{ service_name }}</p>
                {% if token_refreshed %}
                    <p class="success">✅ Token was expired and has been refreshed</p>
                {% endif %}
            {% elif token_exists %}
                <p class="error">❌ Authentication failed or token is invalid</p>
                {% if error %}
                    <p class="error">Error: {{ error }}</p>
                {% endif %}
            {% endif %}
        </div>
        
        <div class="card">
            <h2>Actions</h2>
            {% if not client_secret_exists %}
                <p class="error">You must create a client_secret.json file before authenticating.</p>
                <p>Follow these steps:</p>
                <ol>
                    <li>Go to the <a href="https://console.cloud.google.com/">Google Cloud Console</a></li>
                    <li>Create a new project or select an existing one</li>
                    <li>Enable the required Google API</li>
                    <li>Create OAuth credentials (Web application type)</li>
                    <li>Add authorized redirect URI: {{ url_for('oauth2callback', _external=True) }}</li>
                    <li>Download the credentials as client_secret.json</li>
                    <li>Save the file in the config directory</li>
                </ol>
            {% elif not token_exists or not authenticated %}
                <p>Click the button below to authorize this application to access {{ service_name }}:</p>
                <p><a href="{{ url_for('authorize') }}" class="button">Authorize with Google</a></p>
            {% else %}
                <p class="success">✅ All set! Your {{ service_name }} is connected.</p>
                <p>If you need to reconnect with a different account:</p>
                <p><a href="{{ url_for('revoke') }}" class="button" style="background: #db4437;">Revoke Access</a></p>
            {% endif %}
        </div>
    </div>
</body>
</html>
            """)
    
    auth_success_path = template_dir / "auth_success.html"
    if not auth_success_path.exists():
        with open(auth_success_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Authentication Successful</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; text-align: center; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; }
        .success { color: green; font-size: 24px; margin: 30px 0; }
        .button { display: inline-block; background: #4285f4; color: white; padding: 10px 20px; 
                 text-decoration: none; border-radius: 4px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ service_name }} Authentication</h1>
        
        <p class="success">✅ Authentication Successful!</p>
        
        <p>Your {{ service_name }} has been successfully connected to the Fridge Kiosk.</p>
        
        <p>You can now close this window and restart your Fridge Kiosk application.</p>
        
        <p><a href="{{ url_for('index') }}" class="button">Back to Main Page</a></p>
    </div>
</body>
</html>
            """)

def run_auth_server(port=8090, service="Google Calendar"):
    """Run the authentication server with the given port and service name"""
    create_template_files()
    
    print(f"\n=== GOOGLE {service.upper()} AUTHENTICATION SERVER ===")
    
    # Try different ports in case the default one is in use
    ports_to_try = [port, 8095, 8100, 8105, 8110]
    
    # If template files don't exist, create them
    auth_index_path = current_dir / "templates" / "auth_index.html"
    if not auth_index_path.exists():
        create_template_files()
    
    import socket
    for port in ports_to_try:
        try:
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            
            print(f"\nStarting authentication server on port {port}")
            print(f"Please open your browser to http://localhost:{port}?service={service.replace(' ', '%20')}\n")
            
            app.run(host='0.0.0.0', port=port)
            break
        except OSError:
            print(f"Port {port} is already in use, trying another port...")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Authentication Server')
    parser.add_argument('--port', type=int, default=8090, help='Port to run the server on')
    parser.add_argument('--service', type=str, default='Google Calendar', 
                      help='Service name (calendar, photos, etc.)')
    
    args = parser.parse_args()
    
    run_auth_server(port=args.port, service=args.service) 