import os
import json
import logging
import random
import requests
import time
import traceback
from google.oauth2.credentials import Credentials
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from http.server import BaseHTTPRequestHandler

# Get plugin-specific logger
logger = logging.getLogger('plugins.google-photos')

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'photos_cache.json')
CACHE_EXPIRY = 90 * 24 * 3600  # 90 days cache expiry

# Error handling and backoff configuration
ERROR_STATE_FILE = os.path.join(CACHE_DIR, 'error_state.json')
DEFAULT_REFRESH_INTERVAL = 300  # 5 minutes default
MAX_REFRESH_INTERVAL = 3600     # 1 hour maximum
ERROR_BACKOFF_MULTIPLIER = 2    # Double the interval each failure
MAX_CONSECUTIVE_ERRORS = 10     # Stop trying after 10 consecutive errors

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")

def load_cache():
    ensure_cache_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                # Check if cache is expired
                if time.time() - cache.get('timestamp', 0) < CACHE_EXPIRY:
                    logger.info("Using cached data")
                    return cache
                else:
                    logger.info("Cache expired")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    return None

def save_cache(cache_data):
    ensure_cache_dir()
    try:
        cache_data['timestamp'] = time.time()
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.info("Cache saved successfully")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def get_credentials():
    """Get valid credentials from token.json or return None."""
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'token.json')
    logger.debug(f"Looking for token.json at: {token_path}")
    
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                logger.debug(f"Successfully loaded token.json with keys: {list(token_data.keys())}")
                credentials = Credentials(**token_data)
                
                # Check if credentials are valid
                if credentials.expired:
                    logger.warning("Credentials are expired")
                    if credentials.refresh_token:
                        logger.info("Attempting to refresh credentials")
                        from google.auth.transport.requests import Request
                        credentials.refresh(Request())
                        logger.info("Credentials refreshed successfully")
                        
                        # Save refreshed credentials back to token.json
                        refreshed_token_data = {
                            'token': credentials.token,
                            'refresh_token': credentials.refresh_token,
                            'token_uri': credentials.token_uri,
                            'client_id': credentials.client_id,
                            'client_secret': credentials.client_secret,
                            'scopes': credentials.scopes
                        }
                        with open(token_path, 'w') as token_file:
                            json.dump(refreshed_token_data, token_file, indent=2)
                        logger.info("Refreshed credentials saved to token.json")
                    else:
                        logger.error("No refresh token available")
                        return None
                
                logger.info("Credentials loaded and validated successfully")
                logger.debug(f"Credential scopes: {credentials.scopes}")
                return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            logger.debug(f"Token file path: {token_path}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
    else:
        logger.warning(f"token.json not found at {token_path}")
    return None

def get_photos_session():
    """Get a Google Photos API session."""
    logger.debug("Attempting to get photos session")
    credentials = get_credentials()
    if not credentials:
        logger.error("No valid credentials found")
        return None

    # Force refresh the credentials to ensure we have the latest token
    try:
        if credentials.refresh_token:
            logger.info("Forcing credential refresh for Photos API")
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
            logger.info("Credentials refreshed successfully for Photos API")
            
            # Save the refreshed token
            token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'token.json')
            refreshed_token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            with open(token_path, 'w') as token_file:
                json.dump(refreshed_token_data, token_file, indent=2)
            logger.info("Updated token.json with fresh credentials")
    except Exception as e:
        logger.error(f"Error refreshing credentials for Photos API: {e}")

    try:
        service = build(
            'photoslibrary', 'v1', credentials=credentials,
            discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
        )
        logger.debug("Successfully created Photos API service")
        logger.debug(f"Using credentials with scopes: {credentials.scopes}")
        return service
    except Exception as e:
        logger.error(f"Error creating Photos API service: {e}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        return None

def list_albums():
    """List all albums in the user's Google Photos library, with caching."""
    logger.debug("Attempting to list albums (with cache)")
    # Try to load from cache first
    cache = load_cache()
    if cache and 'albums' in cache:
        logger.info(f"Using cached album list with {len(cache['albums'])} albums")
        return cache['albums']

    # If not cached, fetch from API
    service = get_photos_session()
    if not service:
        logger.error("No valid service session for listing albums")
        return []
    try:
        results = service.albums().list(pageSize=50).execute()
        albums = results.get('albums', [])
        logger.info(f"Found {len(albums)} albums (from API)")
        logger.debug(f"Album list response: {json.dumps(results, indent=2)}")
        # Save to cache
        save_cache({'albums': albums})
        return albums
    except HttpError as error:
        error_message = str(error)
        logger.error(f"Error listing albums: {error}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        
        # Record error for backoff handling
        if "quota exceeded" in error_message.lower() or "rate limit" in error_message.lower() or error.resp.status == 429:
            record_api_error("quota_exceeded", error_message)
        elif error.resp.status == 403:
            record_api_error("permission_denied", error_message)
        else:
            record_api_error("http_error", error_message)
        
        return []

def list_media_items_in_album(album_id):
    """List all media items in a specific album."""
    logger.debug(f"Attempting to list media items in album {album_id}")
    service = get_photos_session()
    if not service:
        logger.error("No valid service session for listing media items")
        return []

    try:
        # Use the 'search' method, not 'list', and provide albumId in the body
        body = {
            "albumId": album_id,
            "pageSize": 100
        }
        results = service.mediaItems().search(body=body).execute()
        media_items = results.get('mediaItems', [])
        logger.info(f"Found {len(media_items)} media items in album {album_id}")
        logger.debug(f"Media items response: {json.dumps(results, indent=2)}")
        return media_items
    except HttpError as error:
        error_message = str(error)
        logger.error(f"Error listing media items: {error}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        
        # Record error for backoff handling
        if "quota exceeded" in error_message.lower() or "rate limit" in error_message.lower() or error.resp.status == 429:
            record_api_error("quota_exceeded", error_message)
        elif error.resp.status == 403:
            record_api_error("permission_denied", error_message)
        else:
            record_api_error("http_error", error_message)
        
        return []

def get_random_photo_batch():
    logger.debug("Starting get_random_photo_batch")
    service = get_photos_session()
    if not service:
        logger.error("No valid service session for getting photo batch")
        return []

    # Load sequence_count from config.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    sequence_count = 6
    try:
        with open(config_path) as f:
            config = json.load(f)
            sequence_count = int(config.get('settings', {}).get('sequence_count', 6))
    except Exception as e:
        logger.warning(f"Could not read sequence_count from config: {e}")

    try:
        # Get all albums
        albums = list_albums()
        if not albums:
            logger.warning("No albums found")
            return []

        # Filter out empty albums
        non_empty_albums = []
        for album in albums:
            try:
                media_count = int(album.get('mediaItemsCount', 0))
                if media_count > 0:
                    non_empty_albums.append(album)
                    logger.debug(f"Album {album['title']} has {media_count} items")
            except ValueError:
                logger.warning(f"Invalid mediaItemsCount for album {album['title']}")

        if not non_empty_albums:
            logger.warning("No non-empty albums found")
            return []

        # Select a random album
        album = random.choice(non_empty_albums)
        logger.info(f"Selected album: {album['title']}")

        # Get all media items in the album
        media_items = list_media_items_in_album(album['id'])
        if not media_items:
            logger.warning(f"No media items found in album {album['title']}")
            return []

        # Use all media items (photos and videos)
        media = media_items  # include both photos and videos
        if not media:
            logger.warning(f"No media items found in album {album['title']}")
            return []

        # Pick a random start index
        total_media = len(media)
        if total_media == 0:
            return []
        start_index = random.randint(0, total_media - 1)

        # Add album info for album line
        total_albums = len(non_empty_albums)
        album_number = non_empty_albums.index(album) + 1 if album in non_empty_albums else 1
        # Build the sequence, wrapping around if needed
        sequence = []
        for i in range(sequence_count):
            idx = (start_index + i) % total_media
            item = media[idx]
            # Add album info
            item['album'] = {
                'id': album['id'],
                'title': album['title']
            }
            # Add counter: remaining in sequence (decreasing)
            item['sequence_remaining'] = sequence_count - i
            # Add total count and current index (1-based)
            item['album_total_count'] = total_media
            item['album_index'] = idx + 1  # 1-based index
            # Add album line info
            item['total_albums'] = total_albums
            item['album_number'] = album_number
            sequence.append(item)

        return sequence

    except Exception as e:
        logger.error(f"Error getting random photo batch: {e}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        return []

def api_data():
    """API endpoint for getting photo data."""
    logger.debug("Starting api_data endpoint")
    
    # Check if we should skip due to recent errors
    should_skip, error_state = should_skip_due_to_errors()
    if should_skip:
        return {
            'error': f'Skipping request due to {error_state["consecutive_errors"]} consecutive errors. '
                    f'Next retry in {error_state["current_interval"] - (time.time() - error_state["last_error_time"]):.0f} seconds.',
            'retry_after': error_state['current_interval'] - (time.time() - error_state['last_error_time'])
        }
    
    try:
        photos = get_random_photo_batch()
        if not photos:
            logger.warning("No photos returned from get_random_photo_batch")
            # This might be due to an error in get_random_photo_batch, check if we should record it
            return {'error': 'No photos available'}
        
        # Success! Reset error state
        record_api_success()
        
        # Log kiekvieną perduodamą media failą kaip WARNING
        for item in photos:
            album = item.get('album', {}).get('title', 'Unknown Album')
            filename = item.get('filename', 'Unknown File')
            media_type = item.get('mimeType', 'unknown')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.warning(f"[DISPLAYED] {now} [{album}] {filename} ({media_type})")
        
        logger.info(f"Returning {len(photos)} photos")
        logger.debug(f"Returning photos: {json.dumps(photos, indent=2)}")
        return {'media': photos}
    except Exception as e:
        logger.error(f"Error in api_data: {e}")
        logger.debug(f"API error traceback: {traceback.format_exc()}")
        
        # Record the error for backoff handling
        error_message = str(e)
        if "quota exceeded" in error_message.lower() or "rate limit" in error_message.lower():
            record_api_error("quota_exceeded", error_message)
        else:
            record_api_error("api_error", error_message)
        
        return {'error': str(e)}

def init(config):
    """Initialize the plugin with configuration."""
    logger.debug("Initializing Google Photos plugin")
    try:
        # Set logger level from config
        log_level = config.get('logging', 'INFO')
        logger.setLevel(getattr(logging, log_level))
        logger.info(f"Logger level set to {logger.level} ({log_level})")
        
        # Log the full config
        logger.debug(f"Config: {json.dumps(config, indent=2)}")
        
        # Initialize cache directory
        ensure_cache_dir()
        
        # Test credentials
        credentials = get_credentials()
        if not credentials:
            logger.error("Failed to initialize: No valid credentials found")
            return {'data': {}, 'error': 'No valid credentials found'}
        
        logger.info("Google Photos plugin initialized successfully")
        logger.propagate = False
        return {'data': {}}
    except Exception as e:
        logger.error(f"Error initializing plugin: {e}")
        logger.debug(f"Init error traceback: {traceback.format_exc()}")
        return {'data': {}, 'error': str(e)}

def load_error_state():
    """Load error state from file."""
    if os.path.exists(ERROR_STATE_FILE):
        try:
            with open(ERROR_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading error state: {e}")
    
    return {
        'consecutive_errors': 0,
        'last_error_time': 0,
        'current_interval': DEFAULT_REFRESH_INTERVAL,
        'last_error_type': None
    }

def save_error_state(error_state):
    """Save error state to file."""
    ensure_cache_dir()
    try:
        with open(ERROR_STATE_FILE, 'w') as f:
            json.dump(error_state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving error state: {e}")

def should_skip_due_to_errors():
    """Check if we should skip this request due to recent errors."""
    error_state = load_error_state()
    
    # If we haven't had recent errors, proceed
    if error_state['consecutive_errors'] == 0:
        return False, error_state
    
    # If we've had max errors, check if enough time has passed
    if error_state['consecutive_errors'] >= MAX_CONSECUTIVE_ERRORS:
        time_since_error = time.time() - error_state['last_error_time']
        if time_since_error < error_state['current_interval']:
            logger.warning(f"Skipping API request due to {error_state['consecutive_errors']} consecutive errors. "
                         f"Will retry in {error_state['current_interval'] - time_since_error:.0f} seconds.")
            return True, error_state
    
    return False, error_state

def record_api_success():
    """Record a successful API call - reset error state."""
    error_state = {
        'consecutive_errors': 0,
        'last_error_time': 0,
        'current_interval': DEFAULT_REFRESH_INTERVAL,
        'last_error_type': None
    }
    save_error_state(error_state)
    logger.info("API success - reset error state to normal refresh interval")

def record_api_error(error_type, error_message):
    """Record an API error and implement exponential backoff."""
    error_state = load_error_state()
    
    error_state['consecutive_errors'] += 1
    error_state['last_error_time'] = time.time()
    error_state['last_error_type'] = error_type
    
    # Exponential backoff: double the interval each time, up to maximum
    if error_state['consecutive_errors'] <= MAX_CONSECUTIVE_ERRORS:
        error_state['current_interval'] = min(
            DEFAULT_REFRESH_INTERVAL * (ERROR_BACKOFF_MULTIPLIER ** error_state['consecutive_errors']),
            MAX_REFRESH_INTERVAL
        )
    
    save_error_state(error_state)
    
    if error_type == "quota_exceeded":
        logger.error(f"Quota exceeded! Will retry in {error_state['current_interval']} seconds. "
                    f"Consecutive errors: {error_state['consecutive_errors']}")
    else:
        logger.warning(f"API error ({error_type}): {error_message}. "
                      f"Will retry in {error_state['current_interval']} seconds. "
                      f"Consecutive errors: {error_state['consecutive_errors']}")

def get_current_refresh_interval():
    """Get the current refresh interval based on error state."""
    error_state = load_error_state()
    return error_state['current_interval']

def api_refresh_interval():
    """API endpoint to get the current refresh interval based on error state."""
    interval = get_current_refresh_interval()
    error_state = load_error_state()
    
    return {
        'refresh_interval': interval,
        'consecutive_errors': error_state['consecutive_errors'],
        'last_error_type': error_state['last_error_type'],
        'status': 'backing_off' if error_state['consecutive_errors'] > 0 else 'normal'
    }

def api_reset_errors():
    """API endpoint to manually reset the error state (for debugging/admin use)."""
    record_api_success()
    return {'message': 'Error state reset to normal', 'refresh_interval': DEFAULT_REFRESH_INTERVAL} 