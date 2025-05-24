#!/usr/bin/env python3
"""
OAuth authentication server for Google Calendar plugin.
This server handles the OAuth flow and stores the credentials.
"""

import os
import json
import logging
import traceback
from pathlib import Path
import requests
from flask import Flask, render_template, redirect, url_for, session, request

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Configure logging to use the common log file
log_file = PROJECT_ROOT / 'logs' / 'fridge-kiosk.log'
log_file.parent.mkdir(exist_ok=True, parents=True)

# Create a custom logger
logger = logging.getLogger('google_calendar_auth')
logger.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(file_handler)

# Force a log message to verify logging is working
logger.info("Google Calendar Auth Server Loaded")

# Get the project root directory
current_dir = Path(__file__).resolve().parent
PROJECT_ROOT = current_dir.parent.parent
CLIENT_SECRET_FILE = PROJECT_ROOT / 'config' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'config' / 'token.json'

# For development only
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Create Flask app
app = Flask(__name__, template_folder=str(current_dir / "templates"))
app.secret_key = os.urandom(24)

# Define OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

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
    # Check if we have stored credentials
    token_exists = TOKEN_FILE.exists()
    client_secret_exists = CLIENT_SECRET_FILE.exists()
    
    context = {
        'token_exists': token_exists,
        'client_secret_exists': client_secret_exists,
        'calendar_id': os.getenv("GOOGLE_CALENDAR_ID", "primary")
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
            
            # Try to access the API to verify credentials
            service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
            calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
            
            # List calendars to verify access
            calendars = service.calendarList().list().execute()
            
            context['authenticated'] = True
            context['calendars'] = calendars.get('items', [])
            context['calendar_count'] = len(calendars.get('items', []))
            
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
    
    # Create OAuth flow
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES
    )
    
    # Set redirect URI
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    # Generate URL for user consent
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    
    # Save state for later verification
    session['state'] = state
    
    # Redirect user to Google's OAuth consent page
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth callback from Google"""
    # Get state we passed earlier
    state = session['state']
    
    # Create flow with the client secret and state
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE, 
        scopes=SCOPES,
        state=state
    )
    
    # Set redirect URI to match the one we used when requesting authorization
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    # Use authorization response from Google
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    # Get credentials from flow
    credentials = flow.credentials
    
    # Ensure we have a refresh token
    if not credentials.refresh_token:
        return "Error: No refresh token received. Please revoke access and try again."
    
    # Save credentials to token.json
    token_data = credentials_to_dict(credentials)
    
    # Create parent directories if needed
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)
    
    # Save to session too
    session['credentials'] = token_data
    
    return redirect(url_for('success'))

@app.route('/success')
def success():
    """Show success page after authentication"""
    return render_template('auth_success.html')

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

if __name__ == '__main__':
    # Create template directory if it doesn't exist
    template_dir = current_dir / "templates"
    template_dir.mkdir(exist_ok=True)
    
    # Try different ports in case the default one is in use
    auth_port = 8090
    ports_to_try = [8090, 8095, 8100, 8105, 8110]
    
    print("\n=== GOOGLE CALENDAR AUTHENTICATION SERVER ===")
    
    # If template files don't exist, create them
    auth_index_path = template_dir / "auth_index.html"
    if not auth_index_path.exists():
        with open(auth_index_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Google Calendar Authentication</title>
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
        <h1>Google Calendar Authentication</h1>
        
        <div class="card">
            <h2>Configuration Status</h2>
            <p><strong>client_secret.json:</strong> {% if client_secret_exists %}✅ Found{% else %}❌ Missing{% endif %}</p>
            <p><strong>token.json:</strong> {% if token_exists %}✅ Found{% else %}❌ Missing{% endif %}</p>
            <p><strong>Calendar ID:</strong> {{ calendar_id }}</p>
            
            {% if authenticated %}
                <p class="success">✅ Successfully authenticated with Google Calendar</p>
                {% if token_refreshed %}
                    <p class="success">✅ Token was expired and has been refreshed</p>
                {% endif %}
                <p>Found {{ calendar_count }} calendars</p>
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
                    <li>Enable the Google Calendar API</li>
                    <li>Create OAuth credentials (Web application type)</li>
                    <li>Add authorized redirect URI: {{ url_for('oauth2callback', _external=True) }}</li>
                    <li>Download the credentials as client_secret.json</li>
                    <li>Save the file in the config directory</li>
                </ol>
            {% elif not token_exists or not authenticated %}
                <p>Click the button below to authorize this application to access your Google Calendar:</p>
                <p><a href="{{ url_for('authorize') }}" class="button">Authorize with Google</a></p>
            {% else %}
                <p class="success">✅ All set! Your Google Calendar is connected.</p>
                <p>If you need to reconnect with a different account:</p>
                <p><a href="{{ url_for('revoke') }}" class="button" style="background: #db4437;">Revoke Access</a></p>
            {% endif %}
        </div>
        
        {% if authenticated and calendars %}
            <div class="card">
                <h2>Your Calendars</h2>
                <p>Current Calendar ID: <strong>{{ calendar_id }}</strong></p>
                <p>Available calendars:</p>
                <ul>
                    {% for calendar in calendars %}
                    <li>
                        <strong>{{ calendar.summary }}</strong><br>
                        ID: {{ calendar.id }}<br>
                        {% if calendar.id == calendar_id %}
                            <span class="success">✅ This is your current calendar</span>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                <p>To change the calendar, set the GOOGLE_CALENDAR_ID in your .env file.</p>
            </div>
        {% endif %}
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
        <h1>Google Calendar Authentication</h1>
        
        <p class="success">✅ Authentication Successful!</p>
        
        <p>Your Google Calendar has been successfully connected to the Fridge Kiosk.</p>
        
        <p>You can now close this window and restart your Fridge Kiosk application.</p>
        
        <p><a href="{{ url_for('index') }}" class="button">Back to Main Page</a></p>
    </div>
</body>
</html>
            """)
    
    # Try different ports
    import socket
    for port in ports_to_try:
        try:
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            auth_port = port
            break
        except OSError:
            print(f"Port {port} is already in use, trying another port...")
    
    print(f"\nStarting authentication server on port {auth_port}")
    print(f"Please open your browser to http://localhost:{auth_port}\n")
    
    port = int(os.environ.get('PORT', auth_port))
    app.run(host='0.0.0.0', port=port) 