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
    """List all albums in the user's Google Photos library."""
    logger.debug("Attempting to list albums")
    service = get_photos_session()
    if not service:
        logger.error("No valid service session for listing albums")
        return []
    
    try:
        results = service.albums().list(pageSize=50).execute()
        albums = results.get('albums', [])
        logger.info(f"Found {len(albums)} albums")
        logger.debug(f"Album list response: {json.dumps(results, indent=2)}")
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
        results = service.mediaItems().list(
            pageSize=100,
            albumId=album_id
        ).execute()
        
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
        
        # Filter for photos only (not videos)
        photos = [item for item in media_items if not item.get('mimeType', '').startswith('video/')]
        if not photos:
            logger.warning(f"No photos found in album {album['title']}")
            return []
        
        # Select a random batch of photos
        batch_size = min(10, len(photos))
        selected_photos = random.sample(photos, batch_size)
        logger.info(f"Selected {batch_size} photos from album {album['title']}")
        
        # Add album information to each photo
        for photo in selected_photos:
            photo['album'] = {
                'id': album['id'],
                'title': album['title']
            }
            logger.debug(f"Added album info to photo: {photo.get('filename', 'unknown')}")
        
        return selected_photos
    
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
            return False
        
        logger.info("Google Photos plugin initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing plugin: {e}")
        logger.debug(f"Init error traceback: {traceback.format_exc()}")
        return False 