import json
import os
import datetime
import sys
from pathlib import Path
import dotenv
from zoneinfo import ZoneInfo
from collections import defaultdict
import logging

# Import local plugin helpers
from .helpers import get_event_color, format_time

# Google Calendar API
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / 'config' / '.env'
CLIENT_SECRET_FILE = PROJECT_ROOT / "config" / "client_secret.json"
TOKEN_FILE = PROJECT_ROOT / "config" / "token.json"

# Load environment variables from the project-wide .env file
dotenv.load_dotenv(ENV_FILE)

# Configure logging to write to both stderr and a file
log_file = PROJECT_ROOT / 'logs' / 'google_calendar.log'
log_file.parent.mkdir(exist_ok=True, parents=True)

# Create a custom logger
logger = logging.getLogger('google_calendar')
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.DEBUG)

# Create file handler
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Force a log message to verify logging is working
logger.info("==========================================")
logger.info("Google Calendar Plugin Loaded")
logger.info(f"Log file location: {log_file}")
logger.info("==========================================")

# If modifying these scopes, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def event_color_filter(event_summary):
    """Template filter to get event color based on summary"""
    return get_event_color(event_summary)

def load_config():
    """Load plugin configuration"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)

def get_event_color(summary):
    """Template filter to get event color based on summary"""
    if not summary:
        return "#000000"  # Default black
    prefix = summary[:2].upper()
    
    # Define color mapping - copied from old project's config.py
    EVENT_COLORS = {
        "PE": "#4d26f0",
        "BU": "#4d26f0",
        "LI": "#003300",
        "LA": "#3e5393", 
        "DA": "#a07ed3",
        "GI": "#660000"
    }
    
    return EVENT_COLORS.get(prefix, "#000000")

def format_time(datetime_str):
    """Format time from ISO format to HH:MM format"""
    dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    return dt.strftime("%H:%M")

def load_stored_credentials():
    """Load credentials from token.json file if it exists"""
    if TOKEN_FILE.exists():
        try:
            logger.info(f"Found token file at {TOKEN_FILE}, loading credentials")
            with open(TOKEN_FILE, 'r') as token_file:
                token_data = json.load(token_file)
                return google.oauth2.credentials.Credentials(**token_data)
        except Exception as e:
            logger.error(f"Error loading token.json: {e}")
    logger.warning("No token.json found or failed to load")
    return None

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
    """Get credentials for Google Calendar API"""
    # First try to load from token.json
    creds = load_stored_credentials()
    
    # If we have creds but they're expired and we can refresh them
    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing expired credentials")
        try:
            creds.refresh(Request())
            # Save refreshed credentials
            with open(TOKEN_FILE, 'w') as token:
                token_data = credentials_to_dict(creds)
                json.dump(token_data, token)
            logger.info("Credentials refreshed and saved")
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            creds = None
            
    # Return valid credentials if we have them
    if creds and not creds.expired:
        logger.info("Using valid credentials")
        return creds
        
    logger.warning("No valid credentials available")
    return None

def get_events(config=None):
    """Get events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable or use default ("primary")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    logger.debug(f"Using calendar ID: {calendar_id}")
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        logger.error("Error: No valid credentials found")
        return {'error': 'No valid credentials found - run "python3 plugins/google-calendar/auth_server.py" and visit http://localhost:8090 to authenticate'}
    
    # Build the service
    try:
        logger.debug("Building Google Calendar service")
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Set timezone
        vilnius_tz = ZoneInfo('Europe/Vilnius')
        
        # Today's date in local timezone
        today = datetime.datetime.now(vilnius_tz).date()
        
        # Start of the week (Monday)
        start_of_week = today - datetime.timedelta(days=today.weekday())
        
        # End date based on weeks_to_show
        weeks_to_show = config.get('options', {}).get('weeks_to_show', 4)
        end_of_range = start_of_week + datetime.timedelta(days=(weeks_to_show * 7) - 1)
        
        # Format for API
        time_min = start_of_week.isoformat() + 'T00:00:00Z'
        time_max = end_of_range.isoformat() + 'T23:59:59Z'
        
        logger.debug(f"Fetching events from {time_min} to {time_max}")
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            timeZone='Europe/Vilnius'
        ).execute()
        
        events = events_result.get('items', [])
        
        logger.debug(f"Retrieved {len(events)} events from calendar API")
        
        # Process events: add colors and format times
        for event in events:
            if "summary" in event:
                event["color"] = get_event_color(event["summary"])
            else:
                event["color"] = get_event_color("")
            
            # Add formatted time for the template
            if "start" in event and "dateTime" in event["start"]:
                event["formatted_time"] = format_time(event["start"]["dateTime"])
        
        # Group events by day
        events_by_day = defaultdict(list)
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            day_str = start[:10]  # YYYY-MM-DD
            events_by_day[day_str].append(event)
        
        # Generate list of days for the calendar
        weeks = []
        cur_day = start_of_week
        for _ in range(weeks_to_show):
            week = []
            for __ in range(7):
                # Create date string in YYYY-MM-DD format for template
                day_str = cur_day.strftime("%Y-%m-%d")
                # Add day of month as a separate field
                day_info = {
                    "date": cur_day,
                    "day": cur_day.day,
                    "weekday": cur_day.weekday(),
                    "is_today": (cur_day == today),
                    "date_str": day_str
                }
                week.append(day_info)
                cur_day = cur_day + datetime.timedelta(days=1)
            weeks.append(week)
        
        # Create response data
        response = {
            'weeks': weeks,
            'events_by_day': dict(events_by_day),
            'today': today.strftime("%Y-%m-%d"),
            'holidays': config.get('holidays', {}),
            'summary_max_length': config.get('options', {}).get('event_summary_max_length', 28),
            'show_holidays': config.get('options', {}).get('show_holidays', True)
        }
        
        logger.debug(f"Calendar response created with {len(weeks)} weeks")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'error': str(e)}

def get_today_events(config=None):
    """Get only today's events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable or use default ("primary")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    logger.debug(f"Using calendar ID for today's events: {calendar_id}")
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        logger.error("Error: No valid credentials found")
        return {'error': 'No valid credentials found - run "python3 plugins/google-calendar/auth_server.py" and visit http://localhost:8090 to authenticate'}
    
    # Build the service
    try:
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Set timezone
        vilnius_tz = ZoneInfo('Europe/Vilnius')
        
        # Today's midnight in location time
        now = datetime.datetime.now(vilnius_tz)
        local_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Day end (23:59:59)
        local_end = local_midnight + datetime.timedelta(days=1, seconds=-1)
        
        # Convert to ISO format
        time_min = local_midnight.isoformat()
        time_max = local_end.isoformat()
        
        logger.debug(f"Fetching today's events from {time_min} to {time_max}")
        
        # Call the Calendar API
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            timeZone='Europe/Vilnius'
        ).execute()
        
        events = events_result.get('items', [])
        
        logger.debug(f"Retrieved {len(events)} events for today")
        
        # Process events: add colors and format times
        for event in events:
            if "summary" in event:
                event["color"] = get_event_color(event["summary"])
            else:
                event["color"] = get_event_color("")
            
            # Add formatted time for the template
            if "start" in event and "dateTime" in event["start"]:
                event["formatted_time"] = format_time(event["start"]["dateTime"])
        
        return {
            'events': events,
            'summary_max_length': config.get('options', {}).get('event_summary_max_length', 28)
        }
        
    except Exception as e:
        logger.error(f"Error fetching today's events: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'error': str(e)}

def api_data():
    """API endpoint for calendar data"""
    logger.debug("Calendar api_data called")
    return get_events()

def api_today():
    """API endpoint for today's events"""
    logger.debug("Calendar api_today called")
    return get_today_events()

def api_auth():
    """API endpoint to explicitly trigger authentication flow"""
    logger.debug("Calendar api_auth called")
    # Force a new authentication flow
    if TOKEN_FILE.exists():
        logger.debug(f"Removing existing token.json at {TOKEN_FILE}")
        try:
            os.remove(TOKEN_FILE)
        except Exception as e:
            logger.error(f"Error removing token.json: {e}")
    
    # Get new credentials
    creds = get_credentials()
    if creds:
        return {"status": "success", "message": "Authentication successful"}
    else:
        return {"status": "error", "message": "Authentication failed"}

def api_status():
    """API endpoint to check the plugin's status and configuration"""
    logger.debug("Calendar api_status called")
    
    # Check environment variables
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    env_vars = {k: v for k, v in os.environ.items() if 'GOOGLE' in k or 'CALENDAR' in k}
    
    # Check files
    client_secret_exists = CLIENT_SECRET_FILE.exists()
    token_exists = TOKEN_FILE.exists()
    env_file_exists = ENV_FILE.exists()
    
    # Check directories
    project_root_exists = PROJECT_ROOT.exists()
    config_dir_exists = (PROJECT_ROOT / "config").exists()
    
    # Build status response
    status = {
        "plugin": "Google Calendar",
        "status": "checking",
        "environment": {
            "calendar_id": calendar_id,
            "environment_variables": env_vars,
            "current_directory": os.getcwd(),
            "python_path": sys.path,
        },
        "files": {
            "client_secret.json": client_secret_exists,
            "token.json": token_exists,
            ".env": env_file_exists,
        },
        "directories": {
            "project_root_path": str(PROJECT_ROOT),
            "project_root_exists": project_root_exists,
            "config_dir_exists": config_dir_exists,
        },
        "logs": {
            "log_file": str(log_file),
        }
    }
    
    # Try to load config
    try:
        config = load_config()
        status["config"] = config
    except Exception as e:
        status["config_error"] = str(e)
    
    # Try to check credentials
    try:
        creds = get_credentials()
        status["credentials"] = {
            "available": creds is not None,
            "valid": creds is not None and not getattr(creds, 'expired', True),
            "refreshable": creds is not None and getattr(creds, 'refresh_token', None) is not None,
        }
    except Exception as e:
        status["credentials_error"] = str(e)
    
    status["status"] = "ok" if client_secret_exists else "missing_client_secret"
    
    logger.debug(f"Status response: {status}")
    return status

def get_refresh_interval():
    """Get refresh interval from config"""
    config = load_config()
    return config.get('updateInterval', 900)

def init(config):
    """Initialize the plugin"""
    # Log the plugin initialization
    logger.info("Initializing Google Calendar plugin")
    
    try:
        # Check if client_secret.json exists
        if not CLIENT_SECRET_FILE.exists():
            logger.error(f"client_secret.json not found at {CLIENT_SECRET_FILE}")
            return {'data': {}, 'error': 'Client secret file not found - please create it first'}
        
        # Log environment variables for debugging
        logger.debug(f"Project root: {PROJECT_ROOT}")
        logger.debug(f"ENV_FILE path: {ENV_FILE}")
        logger.debug(f"ENV_FILE exists: {ENV_FILE.exists()}")
        
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                env_content = f.read()
                logger.debug(f"ENV file content: {env_content}")
        
        env_vars = {k: v for k, v in os.environ.items() if 'GOOGLE' in k or 'CALENDAR' in k}
        logger.debug(f"Relevant environment variables: {env_vars}")
        
        # Check if we need to authenticate
        if not TOKEN_FILE.exists():
            logger.debug("No token.json found, attempting to start authentication flow")
            creds = get_credentials()
            if not creds:
                logger.error("Failed to get credentials during initialization")
                return {'data': {}, 'error': 'Authentication required - run "python3 plugins/google-calendar/auth_server.py" and visit http://localhost:8090 to authenticate'}
        
        # Try to get the events
        data = get_events(config)
        if 'error' in data:
            logger.error(f"Error getting events: {data['error']}")
            return {'data': data, 'error': data['error']}
            
        logger.info(f"Google Calendar plugin initialized successfully with {len(data.get('events_by_day', {}))} days of events")
        return {'data': data}
    except Exception as e:
        logger.error(f"Error initializing Google Calendar plugin: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'data': {}, 'error': str(e)} 