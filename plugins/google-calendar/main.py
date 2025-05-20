import json
import os
import datetime
from pathlib import Path
import dotenv
from zoneinfo import ZoneInfo
from collections import defaultdict

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

def load_config():
    """Load plugin configuration"""
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)

def get_credentials():
    """Get credentials for Google Calendar API"""
    # The file token.json stores the user's access and refresh tokens
    token_path = Path(__file__).parent / "token.json"
    creds = None
    
    # Load client secrets file
    client_secrets_file = Path(__file__).parent / "client_secret.json"
    
    # Check if token.json exists
    if token_path.exists():
        creds = Credentials.from_authorized_user_info(
            json.loads(token_path.read_text()), 
            ['https://www.googleapis.com/auth/calendar.readonly']
        )

    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if client_secrets_file.exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file,
                    ['https://www.googleapis.com/auth/calendar.readonly']
                )
                creds = flow.run_local_server(port=0)
            else:
                return None
                
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

def get_events(config=None):
    """Get events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable
    calendar_id = os.getenv("FAMILY_CALENDAR_ID")
    if not calendar_id:
        print("Error: FAMILY_CALENDAR_ID not set in environment variables")
        return {}
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        print("Error: No valid credentials found")
        return {}
    
    # Build the service
    try:
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
        
        return response
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return {}

def get_today_events(config=None):
    """Get only today's events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable
    calendar_id = os.getenv("FAMILY_CALENDAR_ID")
    if not calendar_id:
        print("Error: FAMILY_CALENDAR_ID not set in environment variables")
        return {}
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        print("Error: No valid credentials found")
        return {}
    
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
        print(f"Error fetching today's events: {e}")
        return {}

def api_data():
    """API endpoint for calendar data"""
    return get_events()

def api_today():
    """API endpoint for today's events"""
    return get_today_events()

def get_refresh_interval():
    """Get refresh interval from config"""
    config = load_config()
    return config.get('updateInterval', 900)

def init(config):
    """Initialize the plugin"""
    return {'data': get_events(config)} 