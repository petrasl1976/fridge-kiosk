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

# Get plugin-specific logger
logger = logging.getLogger('plugins.google-photos')

# Cache configuration
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
CACHE_FILE = os.path.join(CACHE_DIR, 'photos_cache.json')
CACHE_EXPIRY = 90 * 24 * 3600  # 90 days cache expiry

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
                        credentials.refresh(None)
                        logger.info("Credentials refreshed successfully")
                    else:
                        logger.error("No refresh token available")
                        return None
                
                logger.info("Credentials loaded and validated successfully")
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

    try:
        service = build(
            'photoslibrary', 'v1', credentials=credentials,
            discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
        )
        logger.debug("Successfully created Photos API service")
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
        logger.error(f"Error listing albums: {error}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
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
        logger.error(f"Error listing media items: {error}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
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
            sequence.append(item)

        return sequence

    except Exception as e:
        logger.error(f"Error getting random photo batch: {e}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        return []

def api_data():
    """API endpoint for getting photo data."""
    logger.debug("Starting api_data endpoint")
    try:
        photos = get_random_photo_batch()
        if not photos:
            logger.warning("No photos returned from get_random_photo_batch")
            return {'error': 'No photos available'}
        
        logger.info(f"Returning {len(photos)} photos")
        logger.debug(f"Returning photos: {json.dumps(photos, indent=2)}")
        return {'media': photos}
    except Exception as e:
        logger.error(f"Error in api_data: {e}")
        logger.debug(f"API error traceback: {traceback.format_exc()}")
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
        return {'data': {}}
    except Exception as e:
        logger.error(f"Error initializing plugin: {e}")
        logger.debug(f"Init error traceback: {traceback.format_exc()}")
        return {'data': {}, 'error': str(e)} 