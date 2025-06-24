import os
import json
import logging
import random
import requests
import time
import traceback
import inspect
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Get plugin-specific logger
logger = logging.getLogger('plugins.google-picker')

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
SELECTED_PHOTOS_FILE = os.path.join(CACHE_DIR, 'selected_photos.json')
CACHE_EXPIRY = 7 * 24 * 3600  # 7 days cache expiry for photos

# ------------------------------------------------------------
# NEW: Google Photos Library API helpers (for app-created albums)
# ------------------------------------------------------------

# Required scopes according to 2025 policy changes
# - photoslibrary.appendonly
# - photoslibrary.edit.appcreateddata  (for batchAdd/Remove)
# - photoslibrary.readonly.appcreateddata (listing)

def get_photos_service():
    """Return Google Photos Library API service (app-created data only)."""
    logger.debug("Creating Photos Library API service")
    credentials = get_credentials()
    if not credentials:
        logger.error("No credentials available for Photos service")
        return None

    try:
        # Refresh if needed (safe, does not alter scopes)
        if credentials.expired and credentials.refresh_token:
            logger.info("Refreshing expired credentials for Photos service")
            credentials.refresh(Request())

        service = build(
            'photoslibrary', 'v1', credentials=credentials,
            discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
        )
        logger.debug("Photos service created successfully")
        return service
    except Exception as e:
        logger.error(f"Error creating Photos service: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return None

def list_app_albums():
    """Return list of albums created by this app."""
    service = get_photos_service()
    if not service:
        return []

    albums = []
    page_token = None
    try:
        while True:
            results = service.albums().list(
                pageSize=50,
                pageToken=page_token
            ).execute()
            albums.extend(results.get('albums', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        logger.info(f"Fetched {len(albums)} app-created albums")
    except HttpError as error:
        logger.error(f"Error listing app albums: {error}")
    return albums

def create_app_album(title):
    """Create a new album with given title."""
    service = get_photos_service()
    if not service:
        return None, 'No valid photoslibrary service'
    try:
        body = {"album": {"title": title}}
        result = service.albums().create(body=body).execute()
        logger.info(f"Created album '{title}' (id={result.get('id')})")
        return result, None
    except HttpError as error:
        logger.error(f"Error creating album: {error}")
        return None, str(error)

def add_media_items_to_album(album_id, media_item_ids):
    """Add up to many media items to album, chunking by 50."""
    service = get_photos_service()
    if not service:
        return 'No valid photoslibrary service'

    # Ensure list
    if isinstance(media_item_ids, str):
        media_item_ids = [mid.strip() for mid in media_item_ids.split(',') if mid.strip()]

    try:
        for i in range(0, len(media_item_ids), 50):
            chunk = media_item_ids[i:i+50]
            body = {
                "albumId": album_id,
                "mediaItemIds": chunk
            }
            service.albums().batchAddMediaItems(body=body).execute()
            logger.debug(f"Added chunk of {len(chunk)} items to album {album_id}")
        logger.info(f"Added total {len(media_item_ids)} items to album {album_id}")
        return None  # No error
    except HttpError as error:
        logger.error(f"Error adding media items: {error}")
        return str(error)

# ------------------------------------------------------------
# NEW: API endpoints exposed to frontend
# ------------------------------------------------------------

_import_sessions = {}

def _create_picker_session():
    """Helper to create Picker session via API."""
    service = get_picker_service()
    if not service:
        return None, 'No picker service'
    try:
        response = service.sessions().create().execute()
        return response, None
    except HttpError as e:
        logger.error(f"Error creating picker session: {e}")
        return None, str(e)

def api_start_import(query):
    """Start import flow for given albumId; returns pickerUri, sessionId."""
    if not query or 'albumId' not in query:
        return {'error': 'albumId parameter required'}
    album_id = query['albumId'][0]
    session_info, err = _create_picker_session()
    if err or not session_info:
        return {'error': err or 'Failed to create session'}
    session_id = session_info['id']
    _import_sessions[session_id] = {
        'albumId': album_id,
        'created': time.time()
    }
    return {
        'sessionId': session_id,
        'pickerUri': session_info['pickerUri'],
        'pollInterval': session_info.get('pollingConfig', {}).get('pollInterval', 5)
    }

def api_poll_import(query):
    """Poll picker session; if finished, transfer items to album."""
    if not query or 'sessionId' not in query:
        return {'error': 'sessionId is required'}
    session_id = query['sessionId'][0]
    if session_id not in _import_sessions:
        return {'error': 'Unknown sessionId'}
    album_id = _import_sessions[session_id]['albumId']

    service = get_picker_service()
    if not service:
        return {'error': 'No picker service'}
    try:
        response = service.sessions().get(sessionId=session_id).execute()
        if not response.get('mediaItemsSet', False):
            return {'status': 'waiting'}

        # Retrieve selected media items (IDs only)
        ids = []
        page_token = None
        while True:
            if page_token:
                res = service.mediaItems().list(sessionId=session_id, pageToken=page_token).execute()
            else:
                res = service.mediaItems().list(sessionId=session_id).execute()
            batch = res.get('mediaItems', [])
            for item in batch:
                mid = item.get('id') or item.get('mediaItemId') or ''
                if mid:
                    ids.append(mid)
            page_token = res.get('nextPageToken')
            if not page_token:
                break

        err = add_media_items_to_album(album_id, ids)
        if err:
            return {'error': err}

        # Cleanup session reference
        _import_sessions.pop(session_id, None)
        return {'status': 'completed', 'added': len(ids)}
    except HttpError as e:
        logger.error(f"Error polling session: {e}")
        return {'error': str(e)}

def api_albums(query=None):
    """Return list of app albums."""
    albums = list_app_albums()
    # Simplify structure for frontend
    simple = [{
        'id': a.get('id'),
        'title': a.get('title'),
        'mediaItemsCount': a.get('mediaItemsCount', '0')
    } for a in albums]
    return {'albums': simple}

def api_create_album(query):
    """Create album. Expected query param 'title'."""
    if not query or 'title' not in query:
        return {'error': 'Title parameter is required'}
    title = query['title'][0]
    album, err = create_app_album(title)
    if err:
        return {'error': err}
    return {'album': {
        'id': album.get('id'),
        'title': album.get('title')
    }}

def api_add_media_items(query):
    """Add media items to album. Requires 'albumId' & 'ids' (comma-separated)."""
    if not query or 'albumId' not in query or 'ids' not in query:
        return {'error': 'albumId and ids parameters are required'}
    album_id = query['albumId'][0]
    ids_raw = query['ids'][0]
    ids_list = [s.strip() for s in ids_raw.split(',') if s.strip()]
    if not ids_list:
        return {'error': 'No media item IDs provided'}
    err = add_media_items_to_album(album_id, ids_list)
    if err:
        return {'error': err}
    return {'status': 'ok', 'added': len(ids_list)}

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        logger.info(f"Created cache directory: {CACHE_DIR}")

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
                
                logger.info("Credentials loaded successfully")
                logger.debug(f"Credential scopes: {credentials.scopes}")
                logger.info(f"Token expired status: {credentials.expired}")
                return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            logger.debug(f"Token file path: {token_path}")
            logger.debug(f"Error traceback: {traceback.format_exc()}")
    else:
        logger.warning(f"token.json not found at {token_path}")
    return None

def get_picker_service():
    """Get a Google Photos Picker API service."""
    logger.debug("Attempting to get picker service")
    credentials = get_credentials()
    if not credentials:
        logger.error("No valid credentials found")
        return None

    try:
        service = build(
            'photospicker', 'v1', 
            credentials=credentials,
            discoveryServiceUrl='https://photospicker.googleapis.com/$discovery/rest?version=v1'
        )
        logger.debug("Successfully created Picker API service")
        logger.debug(f"Using credentials with scopes: {credentials.scopes}")
        return service
    except Exception as e:
        logger.error(f"Error creating Picker API service: {e}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        return None

def load_selected_photos():
    """Load selected photos from cache."""
    ensure_cache_dir()
    if os.path.exists(SELECTED_PHOTOS_FILE):
        try:
            with open(SELECTED_PHOTOS_FILE, 'r') as f:
                data = json.load(f)
                # Check if cache is expired
                if time.time() - data.get('timestamp', 0) < CACHE_EXPIRY:
                    logger.info(f"Using cached selected photos: {len(data.get('photos', []))} photos")
                    return data.get('photos', [])
                else:
                    logger.info("Selected photos cache expired")
        except Exception as e:
            logger.error(f"Error loading selected photos: {e}")
    return []

def save_selected_photos(photos):
    """Save selected photos to cache."""
    ensure_cache_dir()
    try:
        data = {
            'timestamp': time.time(),
            'photos': photos,
            'total_count': len(photos)
        }
        with open(SELECTED_PHOTOS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(photos)} selected photos to cache")
    except Exception as e:
        logger.error(f"Error saving selected photos: {e}")

def get_random_photo_batch():
    """Get a random batch of photos from selected photos cache."""
    logger.debug("Starting get_random_photo_batch")
    
    # Load sequence_count from config.json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    sequence_count = 6
    try:
        with open(config_path) as f:
            config = json.load(f)
            sequence_count = int(config.get('settings', {}).get('sequence_count', 6))
    except Exception as e:
        logger.warning(f"Could not read sequence_count from config: {e}")

    # Load selected photos
    selected_photos = load_selected_photos()
    if not selected_photos:
        logger.warning("No selected photos found in cache")
        return []

    # Filter photos based on media_types setting
    media_types = "all"
    try:
        with open(config_path) as f:
            config = json.load(f)
            media_types = config.get('settings', {}).get('media_types', 'all')
    except Exception as e:
        logger.warning(f"Could not read media_types from config: {e}")

    filtered_photos = []
    for photo in selected_photos:
        # Handle different possible structures for mimeType
        mime_type = photo.get('mimeType') or photo.get('mediaFile', {}).get('mimeType', '')
        
        if media_types == 'all':
            filtered_photos.append(photo)
        elif media_types == 'photo' and mime_type.startswith('image/'):
            filtered_photos.append(photo)
        elif media_types == 'video' and mime_type.startswith('video/'):
            filtered_photos.append(photo)

    if not filtered_photos:
        logger.warning(f"No photos match media_types filter: {media_types}")
        return []

    # Shuffle all photos and take first sequence_count
    total_photos = len(filtered_photos)
    if total_photos == 0:
        return []
    
    # Randomly shuffle the entire list
    random.shuffle(filtered_photos)
    
    # Take first sequence_count photos
    sequence = []
    for i in range(min(sequence_count, total_photos)):
        photo = filtered_photos[i].copy()
        
        # Normalize the photo structure for frontend consumption
        normalized_photo = normalize_picker_photo(photo)
        
        # Add sequence info
        normalized_photo['sequence_remaining'] = sequence_count - i
        normalized_photo['total_count'] = total_photos
        normalized_photo['photo_index'] = i + 1  # 1-based index
        
        sequence.append(normalized_photo)

    logger.info(f"Returning sequence of {len(sequence)} photos from {total_photos} available")
    return sequence

def normalize_picker_photo(photo):
    """Normalize a Picker API photo to match expected frontend structure."""
    # Handle different possible structures from Picker API
    photo_id = photo.get('id', 'unknown')
    logger.debug(f"Normalizing picker photo: {photo_id}")
    
    normalized = {}
    
    # ID
    normalized['id'] = photo.get('id', '')
    
    # MIME type - could be at root level or in mediaFile
    normalized['mimeType'] = (
        photo.get('mimeType') or 
        photo.get('mediaFile', {}).get('mimeType', 'image/jpeg')
    )
    
    # Base URL - could be at root level or in mediaFile
    normalized['baseUrl'] = (
        photo.get('baseUrl') or 
        photo.get('mediaFile', {}).get('baseUrl', '')
    )
    
    # Media metadata - try to extract dimensions from various possible locations
    media_metadata = photo.get('mediaMetadata', {})
    
    # Try to find dimensions
    width = (
        media_metadata.get('width') or
        photo.get('width') or
        photo.get('mediaFile', {}).get('width') or
        ''
    )
    
    height = (
        media_metadata.get('height') or
        photo.get('height') or
        photo.get('mediaFile', {}).get('height') or
        ''
    )
    
    # Create normalized metadata structure
    normalized['mediaMetadata'] = {
        'width': str(width) if width else '',
        'height': str(height) if height else ''
    }
    
    # Copy any additional metadata that might be useful
    if media_metadata:
        for key in ['photo', 'video']:
            if key in media_metadata:
                normalized['mediaMetadata'][key] = media_metadata[key]
    
    return normalized

def api_data():
    """API endpoint for getting photo data."""
    logger.debug("Starting api_data endpoint")
    
    try:
        photos = get_random_photo_batch()
        if not photos:
            logger.warning("No photos returned from get_random_photo_batch")
            return {'media': [], 'error': 'No photos available. Run picker setup first.'}
        
        # Convert Google Photos URLs to data URLs with proper auth
        for i, photo in enumerate(photos):
            logger.debug(f"Processing photo {i+1}/{len(photos)}: {photo.get('filename', 'unknown')}")
            logger.debug(f"Photo has baseUrl: {bool(photo.get('baseUrl'))}")
            
            if photo.get('baseUrl'):
                original_url = photo['baseUrl']
                logger.info(f"Fetching image for {photo.get('filename', 'unknown')}: {original_url[:50]}...")
                try:
                    # Fetch the image with proper OAuth headers and convert to data URL
                    credentials = get_credentials()
                    if credentials:
                        # Check if credentials are still valid
                        if credentials.expired:
                            logger.warning("Credentials expired, attempting refresh...")
                            credentials.refresh(Request())
                        
                        headers = {
                            'Authorization': f'Bearer {credentials.token}',
                            'User-Agent': 'Fridge-Kiosk-Picker/1.0'
                        }
                        
                        # Add image parameters to the URL
                        image_url = f"{original_url}=w1920-h1080"
                        logger.debug(f"Fetching image: {image_url}")
                        
                        response = requests.get(image_url, headers=headers, timeout=15)
                        logger.debug(f"Response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            # Convert to data URL
                            import base64
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            image_data = base64.b64encode(response.content).decode('utf-8')
                            data_url = f"data:{content_type};base64,{image_data}"
                            photo['baseUrl'] = data_url
                            logger.info(f"✅ Successfully converted to data URL: {len(image_data)} bytes")
                        else:
                            logger.error(f"❌ Failed to fetch image: {response.status_code} - {response.text[:100]}")
                            photo['baseUrl'] = ''  # Will trigger error handling in frontend
                    else:
                        logger.error("❌ No credentials available for image fetching")
                        photo['baseUrl'] = ''
                except Exception as e:
                    logger.error(f"❌ Error fetching image {original_url}: {e}")
                    logger.debug(f"Full error: {traceback.format_exc()}")
                    photo['baseUrl'] = ''
            else:
                logger.warning(f"⚠️ Photo {photo.get('filename', 'unknown')} has no baseUrl in cache")
        
        # Log each displayed media item
        for item in photos:
            filename = item.get('filename', 'Unknown File')
            media_type = item.get('mimeType', 'unknown')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.warning(f"[DISPLAYED] {now} [Picker] {filename} ({media_type})")
        
        logger.info(f"Returning {len(photos)} photos")
        logger.debug(f"Returning photos: {json.dumps(photos, indent=2)}")
        return {'media': photos}
    except Exception as e:
        logger.error(f"Error in api_data: {e}")
        logger.debug(f"API error traceback: {traceback.format_exc()}")
        return {'error': str(e)}

def init(config):
    """Initialize the plugin with configuration."""
    logger.debug("Initializing Google Picker plugin")
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
        
        # Check if we have selected photos
        selected_photos = load_selected_photos()
        if not selected_photos:
            logger.warning("No selected photos found. User needs to run picker setup.")
        else:
            logger.info(f"Found {len(selected_photos)} selected photos in cache")
        
        logger.info("Google Picker plugin initialized successfully")
        logger.propagate = False
        return {'data': {}}
    except Exception as e:
        logger.error(f"Error initializing plugin: {e}")
        logger.debug(f"Init error traceback: {traceback.format_exc()}")
        return {'data': {}, 'error': str(e)}

def api_refresh_interval():
    """Return the refresh interval for API calls in seconds."""
    # Since we're using cached photos, we can refresh less frequently
    # Check for new photos every hour
    return 3600  # 1 hour

def get_cache_info():
    """Get information about the current cache."""
    selected_photos = load_selected_photos()
    cache_file_exists = os.path.exists(SELECTED_PHOTOS_FILE)
    
    info = {
        'cache_exists': cache_file_exists,
        'photo_count': len(selected_photos),
        'cache_file': SELECTED_PHOTOS_FILE
    }
    
    if cache_file_exists:
        try:
            stat = os.stat(SELECTED_PHOTOS_FILE)
            info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            info['file_size'] = stat.st_size
        except Exception as e:
            logger.error(f"Error getting cache file stats: {e}")
    
    return info 