import json
import os
import datetime
import sys
from pathlib import Path
import dotenv
from zoneinfo import ZoneInfo
from collections import defaultdict
import logging
import traceback  # Added for detailed stack traces

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Configure logging to use the common log file
log_file = PROJECT_ROOT / 'logs' / 'fridge-kiosk.log'
log_file.parent.mkdir(exist_ok=True, parents=True)

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Load userColors from main.json
MAIN_CONFIG_FILE = PROJECT_ROOT / 'config' / 'main.json'
try:
    with open(MAIN_CONFIG_FILE) as f:
        MAIN_CONFIG = json.load(f)
        USER_COLORS = MAIN_CONFIG.get('userColors', {})
except Exception as e:
    USER_COLORS = {}
    logger.error(f"Could not load userColors from main.json: {e}")

# Define helper functions directly to avoid import issues
def get_event_color(summary):
    """Get event color based on summary using userColors from main.json"""
    logger.debug(f"Getting color for event summary: '{summary}'")
    if not summary:
        logger.debug("Empty summary, returning black color")
        return "#000000"  # Black for empty summaries
    prefix = summary[:2].upper()
    color = USER_COLORS.get(prefix, "#000000")  # Use black as default if no color found
    logger.debug(f"Prefix: '{prefix}', Color: {color}")
    return color

def format_time(datetime_str):
    """Format time from ISO format to HH:MM format"""
    if isinstance(datetime_str, str):
        dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    else:
        dt = datetime_str
    return dt.strftime("%H:%M")

# Google Calendar API
import google.oauth2.credentials
import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

ENV_FILE = PROJECT_ROOT / 'config' / '.env'
CLIENT_SECRET_FILE = PROJECT_ROOT / "config" / "client_secret.json"
TOKEN_FILE = PROJECT_ROOT / "config" / "token.json"

# Load environment variables from the project-wide .env file
dotenv.load_dotenv(ENV_FILE)

# If modifying these scopes, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def event_color_filter(event_summary):
    """Template filter to get event color based on summary"""
    return get_event_color(event_summary)

def load_config():
    """Load plugin configuration"""
    config_path = Path(__file__).parent / "config.json"
    logger.debug(f"Loading config from {config_path}")
    try:
        with open(config_path) as f:
            config = json.load(f)
            logger.debug(f"Config loaded: {json.dumps(config, indent=2)}")
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {}

def load_stored_credentials():
    """Load credentials from token.json file if it exists"""
    logger.debug(f"Checking for token file at {TOKEN_FILE}")
    if TOKEN_FILE.exists():
        try:
            logger.debug(f"Found token file at {TOKEN_FILE}, loading credentials")
            with open(TOKEN_FILE, 'r') as token_file:
                token_data = json.load(token_file)
                logger.debug(f"Token data loaded, keys: {list(token_data.keys())}")
                return google.oauth2.credentials.Credentials(**token_data)
        except Exception as e:
            logger.error(f"Error loading token.json: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
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
    logger.debug("Entering get_credentials()")
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
            logger.debug(f"Traceback: {traceback.format_exc()}")
            creds = None
            
    # Return valid credentials if we have them
    if creds and not creds.expired:
        logger.info("Using valid credentials")
        logger.debug(f"Credential details: token present: {'yes' if creds.token else 'no'}, refresh_token present: {'yes' if creds.refresh_token else 'no'}, expired: {creds.expired}")
        return creds
        
    logger.warning("No valid credentials available")
    return None

def get_events(config=None):
    """Get events from Google Calendar"""
    logger.debug("Entering get_events()")
    if config is None:
        logger.debug("No config provided, loading from file")
        config = load_config()
    
    # Get calendar ID from environment variable or use default ("primary")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    logger.info(f"Using calendar ID: {calendar_id}")
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        logger.error("Error: No valid credentials found")
        return {'error': 'No valid credentials found - run "python3 -m backend.utils.auth.google_auth_server --service "Google Calendar"" and visit the displayed URL to authenticate'}
    
    # Build the service
    try:
        logger.info("Building Google Calendar service")
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
        
        # Set timezone
        vilnius_tz = ZoneInfo('Europe/Vilnius')
        logger.debug(f"Using timezone: Europe/Vilnius")
        
        # Today's date in local timezone
        today = datetime.datetime.now(vilnius_tz).date()
        logger.debug(f"[DEBUG] today initial value: {today} (type: {type(today)})")
        if isinstance(today, str):
            logger.error(f"[BUG] today is str, value: {today}. Converting to datetime.date. Stack:")
            import traceback
            logger.error(traceback.format_stack())
            today = datetime.date.fromisoformat(today)
        logger.debug(f"[DEBUG] today after type check: {today} (type: {type(today)})")
        start_of_week = today - datetime.timedelta(days=today.weekday())
        logger.debug(f"[DEBUG] start_of_week: {start_of_week} (type: {type(start_of_week)})")
        
        # End date based on weeks_to_show
        weeks_to_show = config.get('options', {}).get('weeks_to_show', 4)
        end_of_range = start_of_week + datetime.timedelta(days=(weeks_to_show * 7) - 1)
        
        # Format for API
        time_min = start_of_week.isoformat() + 'T00:00:00Z'
        time_max = end_of_range.isoformat() + 'T23:59:59Z'
        
        logger.info(f"Fetching events from {time_min} to {time_max}")
        logger.debug(f"Query parameters: calendarId={calendar_id}, timeMin={time_min}, timeMax={time_max}, timeZone=Europe/Vilnius")
        
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
        
        logger.info(f"Retrieved {len(events)} events from calendar API")
        if len(events) > 0:
            logger.debug(f"First event: {json.dumps(events[0], indent=2, default=str)}")
        
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
                    "date": cur_day.strftime("%Y-%m-%d"),  # Convert date to string
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
        
        logger.info(f"Calendar response created with {len(weeks)} weeks")
        logger.debug(f"Response keys: {list(response.keys())}")
        logger.debug(f"Today: {response['today']}")
        logger.debug(f"Number of event days: {len(response['events_by_day'])}")
        # If weeks is empty, fall through to fake data below
        if weeks:
            return response
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
    # If we get here, return a minimal fake calendar grid for debug
    logger.warning("Returning minimal fake calendar grid for debug!")
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    weeks_to_show = config.get('options', {}).get('weeks_to_show', 6)
    weeks = []
    cur_day = start_of_week
    for _ in range(weeks_to_show):
        week = []
        for __ in range(7):
            day_str = cur_day.strftime("%Y-%m-%d")
            day_info = {
                "date": cur_day.strftime("%Y-%m-%d"),  # Convert date to string
                "day": cur_day.day,
                "weekday": cur_day.weekday(),
                "is_today": (cur_day == today),
                "date_str": day_str
            }
            week.append(day_info)
            cur_day = cur_day + datetime.timedelta(days=1)
        weeks.append(week)
    return {
        'weeks': weeks,
        'events_by_day': {},
        'today': today.strftime("%Y-%m-%d"),
        'holidays': {},
        'summary_max_length': 28,
        'show_holidays': True
    }

def get_today_events(config=None):
    """Get only today's events from Google Calendar"""
    if config is None:
        config = load_config()
    
    # Get calendar ID from environment variable or use default ("primary")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", os.getenv("GOOGLE_CLIENT_ID", "primary"))
    logger.info(f"Using calendar ID for today's events: {calendar_id}")
    
    # Get credentials
    creds = get_credentials()
    if not creds:
        logger.error("Error: No valid credentials found")
        return {'error': 'No valid credentials found - run "python3 -m backend.utils.auth.google_auth_server --service "Google Calendar"" and visit the displayed URL to authenticate'}
    
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
        
        logger.info(f"Fetching today's events from {time_min} to {time_max}")
        
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
        
        logger.info(f"Retrieved {len(events)} events for today")
        
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
    """API endpoint for getting calendar data"""
    logger.info("Calendar API called")
    return get_events()

def api_today():
    """API endpoint for today's events"""
    logger.info("Calendar api_today called")
    return get_today_events()

def api_auth():
    """API endpoint to explicitly trigger authentication flow"""
    logger.info("Calendar api_auth called")
    # Force a new authentication flow
    if TOKEN_FILE.exists():
        logger.info(f"Removing existing token.json at {TOKEN_FILE}")
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
    logger.info("Calendar api_status called")
    
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
        logger.debug(f"Config error traceback: {traceback.format_exc()}")
    
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
        logger.debug(f"Credentials error traceback: {traceback.format_exc()}")
    
    status["status"] = "ok" if client_secret_exists else "missing_client_secret"
    
    logger.info(f"Status response prepared: {status['status']}")
    logger.debug(f"Full status: {json.dumps(status, indent=2, default=str)}")
    return status

def get_refresh_interval():
    """Get refresh interval from config"""
    config = load_config()
    return config.get('updateInterval', 900)

def init(config):
    """Initialize the plugin"""
    # Log the plugin initialization
    logger.info("Initializing")
    logger.debug(f"Config: {json.dumps(config, indent=2, default=str)}")
    
    try:
        # Check if client_secret.json exists
        if not CLIENT_SECRET_FILE.exists():
            logger.error(f"client_secret.json not found at {CLIENT_SECRET_FILE}")
            return {'data': {}, 'error': 'Client secret file not found - please create it first'}
        
        # Check if we need to authenticate
        if not TOKEN_FILE.exists():
            logger.info("No token.json found, authentication required")
            return {'data': {}, 'error': 'Authentication required - run "python3 -m backend.utils.auth.google_auth_server --service "Google Calendar"" and visit the displayed URL to authenticate'}
        
        # Try to get the events
        data = get_events(config)
        logger.debug(f"get_events returned data keys: {list(data.keys() if isinstance(data, dict) else [])}")
        
        if 'error' in data:
            logger.error(f"Error getting events: {data['error']}")
            return {'data': data, 'error': data['error']}
        
        # Debug view template variables
        try:
            from jinja2 import Environment, FileSystemLoader
            template_path = Path(__file__).parent / "view.html"
            logger.debug(f"Template exists: {template_path.exists()}")
            
            if template_path.exists():
                with open(template_path, 'r') as f:
                    template_content = f.read()
                logger.debug(f"Template first 100 chars: {template_content[:100]}")
                
                # Check template variables
                import re
                variables = re.findall(r'{{\s*([^}|]*)[}|]', template_content)
                logger.debug(f"Template variables: {set(variables)}")
        except Exception as e:
            logger.debug(f"Error analyzing template: {e}")
            
        logger.info(f"Calendar initialized with {len(data.get('events_by_day', {}))} days of events")
        init_result = {'data': data}
        logger.debug(f"Returning init result with keys: {list(init_result.keys())}")
        logger.debug(f"Data keys: {list(init_result['data'].keys())}")
        return init_result
    except Exception as e:
        logger.error(f"Error initializing: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {'data': {}, 'error': str(e)} 

def api_debug():
    """API endpoint for debugging template rendering issues"""
    logger.info("Calendar api_debug called")
    
    try:
        # Get basic events data
        events_data = get_events()
        
        # Add debug info
        debug_data = {
            "plugin_data": events_data,
            "env_vars": {k: v for k, v in os.environ.items() if 'GOOGLE' in k or 'CALENDAR' in k},
            "files": {
                "client_secret_exists": CLIENT_SECRET_FILE.exists(),
                "token_exists": TOKEN_FILE.exists(),
                "env_exists": ENV_FILE.exists(),
                "client_secret_path": str(CLIENT_SECRET_FILE),
                "token_path": str(TOKEN_FILE)
            },
            "current_directory": os.getcwd(),
            "config": load_config()
        }
        
        # Try to load and test the template
        try:
            from jinja2 import Environment, FileSystemLoader
            template_dir = Path(__file__).parent
            template_path = template_dir / "view.html"
            
            if template_path.exists():
                env = Environment(loader=FileSystemLoader(template_dir))
                template = env.get_template("view.html")
                
                # Create a mock plugin object similar to what the frontend would use
                mock_plugin = {
                    'data': events_data,
                    'config': load_config()
                }
                
                # Try to render the template
                try:
                    rendered = template.render(plugin=mock_plugin)
                    debug_data["template_render"] = "success"
                    debug_data["template_length"] = len(rendered)
                    debug_data["template_sample"] = rendered[:500] + "..." if len(rendered) > 500 else rendered
                except Exception as e:
                    debug_data["template_render"] = "error"
                    debug_data["template_error"] = str(e)
                    debug_data["template_error_traceback"] = traceback.format_exc()
            else:
                debug_data["template_exists"] = False
        except Exception as e:
            debug_data["template_processing_error"] = str(e)
        
        return debug_data
    except Exception as e:
        logger.error(f"Exception in api_debug: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {'error': f"Exception in debug endpoint: {str(e)}"} 

if __name__ == '__main__':
    # Test the calendar functionality
    events = get_events()
    print(json.dumps(events, indent=2)) 

logger.info("Loaded") 