#!/usr/bin/env python3
"""
OAuth authentication server for Google Photos plugin.
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

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
CLIENT_SECRET_FILE = PROJECT_ROOT / 'config' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'config' / 'token.json'

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# For development only
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Define OAuth scopes
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

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

def load_stored_credentials():
    """Load credentials from token.json if it exists."""
    if not TOKEN_FILE.exists():
        return None
        
    try:
        with open(TOKEN_FILE, 'r') as token:
            creds_data = json.load(token)
            return google.oauth2.credentials.Credentials.from_authorized_user_info(creds_data)
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

@app.route('/')
def index():
    """Show authentication status and options."""
    creds = load_stored_credentials()
    if creds and not creds.expired:
        return render_template('auth_success.html')
    return render_template('auth_required.html')

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
    """Handle OAuth callback"""
    state = session['state']
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    
    # Use the authorization server's response to fetch the OAuth 2.0 tokens
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    # Store credentials
    credentials = flow.credentials
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    
    return render_template('auth_success.html')

@app.route('/revoke')
def revoke():
    """Revoke access and delete token"""
    if not TOKEN_FILE.exists():
        return render_template('auth_revoke_error.html', error="No token file found")
        
    try:
        creds = load_stored_credentials()
        if creds:
            # Revoke access
            requests.post('https://oauth2.googleapis.com/revoke',
                params={'token': creds.token},
                headers={'content-type': 'application/x-www-form-urlencoded'})
            
            # Delete token file
            TOKEN_FILE.unlink()
            
        return render_template('auth_revoke_success.html')
    except Exception as e:
        logger.error(f"Error revoking access: {e}")
        return render_template('auth_revoke_error.html', error=str(e))

def run_auth_server(port=8090):
    """Run the authentication server"""
    app.run(host='localhost', port=port, debug=True)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Photos Authentication Server')
    parser.add_argument('--port', type=int, default=8090, help='Port to run the server on')
    
    args = parser.parse_args()
    
    run_auth_server(port=args.port) 