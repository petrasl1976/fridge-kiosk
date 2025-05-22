#!/usr/bin/env python3
"""
Repair tool for Google Calendar plugin.
This script helps diagnose and fix issues with the Google Calendar plugin.
"""

import os
import sys
import json
import logging
import subprocess
import webbrowser
from pathlib import Path
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('google-calendar-repair')

# Get the project root directory
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
        print("4. Create OAuth credentials (Web application)")
        print("5. Download the client_secret.json file")
        print(f"6. Save it to: {CLIENT_SECRET_FILE}")
        return False
    
    # Check if token.json exists
    logger.info(f"Checking token.json file: {TOKEN_FILE}")
    logger.info(f"token.json exists: {TOKEN_FILE.exists()}")
    
    if not TOKEN_FILE.exists():
        logger.warning("token.json file not found. We'll need to run the authentication flow.")
    
    return True

def check_required_packages():
    """Check if all required packages are installed"""
    logger.info("Checking for required packages...")
    
    # Module name mappings (package name -> import name)
    package_mappings = {
        "google-auth": "google.auth",
        "google-auth-oauthlib": "google_auth_oauthlib",
        "google-api-python-client": "googleapiclient",
        "flask": "flask"
    }
    
    missing_packages = []
    
    for package, module in package_mappings.items():
        try:
            __import__(module)
            logger.info(f"Package {package} is installed.")
        except ImportError as e:
            logger.error(f"Package {package} is missing: {e}")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error("Some required packages are missing.")
        print("\nPlease install the missing packages using pip:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("All required packages are installed.")
    return True

def start_auth_server():
    """Start the authentication server"""
    logger.info("Starting authentication server...")
    
    # Path to the auth_server.py file
    auth_server_path = current_dir / "auth_server.py"
    
    if not auth_server_path.exists():
        logger.error(f"Auth server script not found at {auth_server_path}")
        return False
    
    try:
        # Make the script executable
        os.chmod(auth_server_path, 0o755)
        
        # Start the auth server in a new process with output capture
        import io
        from queue import Queue, Empty
        import threading
        import re
        
        # Queue for output lines
        output_queue = Queue()
        
        # Function to read output and put in queue
        def read_output(pipe, queue):
            for line in iter(pipe.readline, b''):
                queue.put(line.decode('utf-8'))
            pipe.close()
        
        # Start the server process
        server_process = subprocess.Popen(
            [sys.executable, str(auth_server_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1
        )
        
        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(target=read_output, args=(server_process.stdout, output_queue))
        stderr_thread = threading.Thread(target=read_output, args=(server_process.stderr, output_queue))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for server to start and extract port
        port_pattern = re.compile(r"Starting authentication server on port (\d+)")
        server_url = None
        
        # Try to get output with timeout
        timeout = 10  # seconds
        start_time = time.time()
        
        print("\nStarting authentication server, please wait...")
        
        while time.time() - start_time < timeout:
            try:
                line = output_queue.get(timeout=0.5)
                print(line, end='')  # Print server output
                
                # Check if this line contains the port information
                match = port_pattern.search(line)
                if match:
                    port = match.group(1)
                    server_url = f"http://localhost:{port}"
                    break
            except Empty:
                pass
        
        if not server_url:
            logger.warning("Could not determine server port from output")
            server_url = "http://localhost:8090"  # Default fallback
        
        print(f"\nOpening authentication page in your browser: {server_url}")
        print("If the browser doesn't open automatically, please open it manually.")
        
        # Try to open the browser
        try:
            webbrowser.open(server_url)
        except Exception as e:
            logger.warning(f"Failed to open browser automatically: {e}")
            print(f"Please open {server_url} in your browser to continue.")
        
        print("\nPress Ctrl+C when you have completed the authentication process.")
        
        # Wait for the user to press Ctrl+C
        try:
            while server_process.poll() is None:
                try:
                    line = output_queue.get(timeout=0.5)
                    print(line, end='')  # Print server output
                except Empty:
                    pass
        except KeyboardInterrupt:
            logger.info("Authentication process interrupted by user.")
            # Terminate the server process
            server_process.terminate()
        
        # Check if token.json was created
        if TOKEN_FILE.exists():
            logger.info("Authentication successful! Token file created.")
            return True
        else:
            logger.error("Authentication failed. No token file was created.")
            return False
    
    except Exception as e:
        logger.error(f"Error starting authentication server: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_calendar_access():
    """Test access to Google Calendar API"""
    logger.info("Testing access to Google Calendar API...")
    
    if not TOKEN_FILE.exists():
        logger.error("No token.json file found. Please run the authentication process first.")
        return False
    
    try:
        # Import required packages
        import google.oauth2.credentials
        import googleapiclient.discovery
        from google.auth.transport.requests import Request
        
        # Load the token
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        # Create credentials
        creds = google.oauth2.credentials.Credentials(**token_data)
        
        # Check if token is expired and can be refreshed
        if creds.expired and creds.refresh_token:
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
        
        # Build the calendar service
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Get calendar ID from environment
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
        
        # Try to get a single event to verify access
        events = service.events().list(
            calendarId=calendar_id,
            maxResults=1
        ).execute()
        
        logger.info("Successfully accessed Google Calendar API.")
        logger.info(f"Found {len(events.get('items', []))} events.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing calendar access: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point"""
    logger.info("Starting Google Calendar repair tool...")
    
    if not check_environment():
        logger.error("Environment check failed.")
        return 1
    
    if not check_required_packages():
        logger.error("Required packages check failed.")
        return 1
    
    # If token.json exists, test the calendar access
    if TOKEN_FILE.exists():
        logger.info("Found existing token.json, testing calendar access...")
        if test_calendar_access():
            logger.info("Calendar access test successful!")
            
            # Ask if the user wants to force re-authentication
            print("\nYour Google Calendar is already set up and working.")
            print("Do you want to re-authenticate anyway? (y/N):")
            force_auth = input().strip().lower() == 'y'
            
            if not force_auth:
                logger.info("User chose not to re-authenticate.")
                logger.info("Google Calendar plugin is now configured correctly!")
                return 0
            else:
                logger.info("User chose to force re-authentication.")
                # Delete the existing token to force re-authentication
                try:
                    os.remove(TOKEN_FILE)
                    logger.info("Deleted existing token.json file.")
                except Exception as e:
                    logger.error(f"Failed to delete token.json: {e}")
        else:
            logger.warning("Calendar access test failed. Let's try to re-authenticate.")
            # Delete the invalid token
            try:
                os.remove(TOKEN_FILE)
                logger.info("Deleted invalid token.json file.")
            except Exception as e:
                logger.error(f"Failed to delete token.json: {e}")
    
    # Start authentication server
    print("\nYou need to authenticate with Google to access your calendar.")
    print("This will open a web page where you can sign in to your Google account.")
    print("Do you want to start the authentication process now? (Y/n):")
    
    start_auth = input().strip().lower() != 'n'
    
    if start_auth:
        if start_auth_server():
            if test_calendar_access():
                logger.info("Google Calendar plugin is now configured correctly!")
                return 0
            else:
                logger.error("Authentication succeeded but calendar access test failed.")
                return 1
        else:
            logger.error("Authentication process failed.")
            return 1
    else:
        logger.info("Authentication skipped by user.")
        print("\nYou can run this script again later to complete the authentication.")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 