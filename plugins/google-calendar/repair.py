#!/usr/bin/env python3
"""
Repair tool for Google Calendar plugin.
This script helps diagnose and fix issues with the Google Calendar plugin.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('google-calendar-repair')

# Get the project root directory (three levels up from this file)
current_dir = Path(__file__).resolve().parent
PROJECT_ROOT = current_dir.parent.parent
ENV_FILE = PROJECT_ROOT / 'config' / '.env'
CLIENT_SECRET_FILE = PROJECT_ROOT / 'config' / 'client_secret.json'
TOKEN_FILE = PROJECT_ROOT / 'config' / 'token.json'

def check_environment():
    """Check environment setup for Google Calendar plugin"""
    logger.info("Checking environment for Google Calendar plugin...")
    
    # Check if the config directory exists
    config_dir = PROJECT_ROOT / 'config'
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Config directory: {config_dir}")
    logger.info(f"Config directory exists: {config_dir.exists()}")
    
    if not config_dir.exists():
        logger.error(f"Config directory does not exist: {config_dir}")
        logger.info("Creating config directory...")
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Config directory created successfully.")
        except Exception as e:
            logger.error(f"Failed to create config directory: {e}")
            return False
    
    # Check if .env file exists
    logger.info(f"Checking .env file: {ENV_FILE}")
    logger.info(f".env file exists: {ENV_FILE.exists()}")
    
    env_vars = {}
    if ENV_FILE.exists():
        logger.info("Reading .env file...")
        with open(ENV_FILE, 'r') as f:
            env_content = f.read()
            for line in env_content.splitlines():
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    # Check for required environment variables
    logger.info("Checking environment variables...")
    calendar_id = env_vars.get('GOOGLE_CALENDAR_ID', os.environ.get('GOOGLE_CALENDAR_ID'))
    client_id = env_vars.get('GOOGLE_CLIENT_ID', os.environ.get('GOOGLE_CLIENT_ID'))
    
    logger.info(f"GOOGLE_CALENDAR_ID: {calendar_id}")
    logger.info(f"GOOGLE_CLIENT_ID: {client_id}")
    
    if not calendar_id and not client_id:
        logger.warning("Neither GOOGLE_CALENDAR_ID nor GOOGLE_CLIENT_ID found in environment")
        
        # Ask user for calendar ID
        print("\nPlease enter your Google Calendar ID (or press Enter for 'primary'):")
        user_calendar_id = input().strip() or 'primary'
        
        # Update .env file
        logger.info(f"Writing calendar ID '{user_calendar_id}' to .env file...")
        env_content = f"GOOGLE_CALENDAR_ID={user_calendar_id}\n"
        
        try:
            with open(ENV_FILE, 'w') as f:
                f.write(env_content)
            logger.info("Updated .env file successfully.")
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
            return False
    
    # Check if client_secret.json exists
    logger.info(f"Checking client_secret.json file: {CLIENT_SECRET_FILE}")
    logger.info(f"client_secret.json exists: {CLIENT_SECRET_FILE.exists()}")
    
    if not CLIENT_SECRET_FILE.exists():
        logger.error("client_secret.json file not found!")
        print("\nYou need to create a Google Cloud project and enable the Google Calendar API.")
        print("Then download the client_secret.json file and place it in the config directory.")
        print("Follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project")
        print("3. Enable the Google Calendar API")
        print("4. Create OAuth credentials (Desktop application)")
        print("5. Download the client_secret.json file")
        print(f"6. Save it to: {CLIENT_SECRET_FILE}")
        return False
    
    # Check if token.json exists
    logger.info(f"Checking token.json file: {TOKEN_FILE}")
    logger.info(f"token.json exists: {TOKEN_FILE.exists()}")
    
    if not TOKEN_FILE.exists():
        logger.warning("token.json file not found. We'll need to run the authentication flow.")
    
    return True

def test_auth_flow():
    """Test the authentication flow for Google Calendar API"""
    try:
        # First, check if we have the required packages
        logger.info("Checking for required packages...")
        
        try:
            import google.oauth2.credentials
            import google_auth_oauthlib.flow
            import googleapiclient.discovery
            logger.info("All required packages are installed.")
        except ImportError as e:
            logger.error(f"Missing required package: {e}")
            logger.info("Please install the required packages:")
            logger.info("pip install google-auth google-auth-oauthlib google-api-python-client")
            return False
        
        # If token.json exists, try to load it
        if TOKEN_FILE.exists():
            logger.info("Testing existing token.json...")
            
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                creds = google.oauth2.credentials.Credentials(**token_data)
                
                # Check if token is expired and can be refreshed
                if creds.expired and hasattr(creds, 'refresh_token') and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    logger.info("Token is expired, attempting to refresh...")
                    creds.refresh(Request())
                    
                    # Save refreshed credentials
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump({
                            'token': creds.token,
                            'refresh_token': creds.refresh_token,
                            'token_uri': creds.token_uri,
                            'client_id': creds.client_id,
                            'client_secret': creds.client_secret,
                            'scopes': creds.scopes
                        }, f)
                    
                    logger.info("Token refreshed successfully.")
                
                # Try to use the credentials to access the Calendar API
                logger.info("Testing access to Google Calendar API...")
                
                # Load environment variables
                env_vars = {}
                if ENV_FILE.exists():
                    with open(ENV_FILE, 'r') as f:
                        env_content = f.read()
                        for line in env_content.splitlines():
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                env_vars[key.strip()] = value.strip()
                
                calendar_id = env_vars.get('GOOGLE_CALENDAR_ID', os.environ.get('GOOGLE_CALENDAR_ID', 'primary'))
                logger.info(f"Using calendar ID: {calendar_id}")
                
                service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
                
                # Try to get a single event to verify access
                events = service.events().list(
                    calendarId=calendar_id,
                    maxResults=1
                ).execute()
                
                logger.info("Successfully accessed Google Calendar API.")
                logger.info(f"Found {len(events.get('items', []))} events.")
                
                return True
                
            except Exception as e:
                logger.error(f"Error testing existing token: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                # Token is invalid or cannot be refreshed, need to generate a new one
                logger.info("Token is invalid or cannot be refreshed. Removing token.json...")
                TOKEN_FILE.unlink(missing_ok=True)
        
        # If we get here, we need to run the OAuth flow
        logger.info("Running OAuth flow to generate new token...")
        
        # If client_secret.json doesn't exist, we can't proceed
        if not CLIENT_SECRET_FILE.exists():
            logger.error(f"client_secret.json not found at {CLIENT_SECRET_FILE}")
            return False
        
        # Run the OAuth flow
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        # If modifying these scopes, delete the token.json file.
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )
        
        # Run the OAuth flow with a local server
        logger.info("Opening browser for authentication...")
        creds = flow.run_local_server(port=8080)
        
        # Save the credentials
        token_data = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
        
        logger.info(f"Saved new token to {TOKEN_FILE}")
        
        # Test the new token
        logger.info("Testing new token with Google Calendar API...")
        
        # Load environment variables
        env_vars = {}
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                env_content = f.read()
                for line in env_content.splitlines():
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        calendar_id = env_vars.get('GOOGLE_CALENDAR_ID', os.environ.get('GOOGLE_CALENDAR_ID', 'primary'))
        logger.info(f"Using calendar ID: {calendar_id}")
        
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Try to get a single event to verify access
        events = service.events().list(
            calendarId=calendar_id,
            maxResults=1
        ).execute()
        
        logger.info("Successfully accessed Google Calendar API.")
        logger.info(f"Found {len(events.get('items', []))} events.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in auth flow: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point"""
    logger.info("Starting Google Calendar repair tool...")
    
    if not check_environment():
        logger.error("Environment check failed.")
        return 1
    
    if not test_auth_flow():
        logger.error("Authentication flow failed.")
        return 1
    
    logger.info("Google Calendar plugin is now configured correctly!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 