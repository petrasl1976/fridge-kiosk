import json
import os
import datetime
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

# Load environment variables from the project-wide .env file
dotenv.load_dotenv(ENV_FILE)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

def credentials_to_dict(credentials):
    """Convert credentials object to dictionary"""
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
    # The file token.json stores the user's access and refresh tokens
    token_path = PROJECT_ROOT / "config" / "token.json"
    
    logger.debug(f"Looking for token.json at: {token_path}")
    
    # First try to load from token.json
    if token_path.exists():
        try:
            logger.debug("Found token.json, attempting to load credentials")
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                return google.oauth2.credentials.Credentials(**token_data)
        except Exception as e:
            logger.error(f"Error loading credentials from token.json: {e}")
    else:
        logger.debug("token.json not found, will need to run auth flow")
    
    # If no token or failed to load, initialize the flow
    client_secrets_file = PROJECT_ROOT / "config" / "client_secret.json"
    if not client_secrets_file.exists():
        logger.error(f"client_secret.json not found at {client_secrets_file}")
        return None
    
    try:
        logger.debug(f"Found client_secret.json, initializing OAuth flow")
        # Create the flow instance
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file,
            SCOPES
        )
        
        # Run the OAuth flow
        logger.debug("Starting OAuth flow with local server")
        creds = flow.run_local_server(port=8080)
        
        # Save the credentials for the next run
        token_data = credentials_to_dict(creds)
        logger.debug(f"OAuth flow completed, saving credentials to {token_path}")
        
        # Create parent directories if they don't exist
        token_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(token_path, 'w') as token:
            json.dump(token_data, token)
        
        return creds
    except Exception as e:
        logger.error(f"Error during authentication flow: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_events(config=None):
    """Get events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable or use default ("primary")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    logger.debug(f"Using calendar ID: {calendar_id}")
    
    # Check environment variables
    env_vars = {k: v for k, v in os.environ.items() if 'GOOGLE' in k or 'CALENDAR' in k}
    logger.debug(f"Relevant environment variables: {env_vars}")
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        logger.error("Error: No valid credentials found")
        return {'error': 'No valid credentials found - you need to authenticate'}
    
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
        return {'error': 'No valid credentials found - you need to authenticate'}
    
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
        client_secrets_file = PROJECT_ROOT / "config" / "client_secret.json"
        if not client_secrets_file.exists():
            logger.error(f"client_secret.json not found at {client_secrets_file}")
            return {'data': {}, 'error': 'Client secret file not found'}
        
        # Log environment variables for debugging
        logger.debug(f"Project root: {PROJECT_ROOT}")
        logger.debug(f"ENV_FILE path: {ENV_FILE}")
        logger.debug(f"ENV_FILE exists: {ENV_FILE.exists()}")
        
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                logger.debug(f"ENV file content: {f.read()}")
        
        env_vars = {k: v for k, v in os.environ.items() if 'GOOGLE' in k or 'CALENDAR' in k}
        logger.debug(f"Relevant environment variables: {env_vars}")
        
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