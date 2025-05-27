import os
import json
import logging
import random
import requests
import time
from google.oauth2.credentials import Credentials
from pathlib import Path
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Get plugin-specific logger
logger = logging.getLogger('plugins.google-photos')
logger.setLevel(logging.DEBUG)  # Default level until config is loaded

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
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                logger.debug("Successfully loaded token.json")
                return Credentials(**token_data)
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            logger.debug(f"Token file path: {token_path}")
    else:
        logger.warning(f"token.json not found at {token_path}")
    return None

def get_photos_session():
    """Get a Google Photos API session."""
    credentials = get_credentials()
    if not credentials:
        logger.error("No valid credentials found")
        return None
    
    try:
        service = build('photoslibrary', 'v1', credentials=credentials)
        logger.debug("Successfully created Photos API service")
        return service
    except Exception as e:
        logger.error(f"Error creating Photos API service: {e}")
        return None

def list_albums():
    """List all albums in the user's Google Photos library."""
    service = get_photos_session()
    if not service:
        return []
    
    try:
        results = service.albums().list(pageSize=50).execute()
        albums = results.get('albums', [])
        logger.info(f"Found {len(albums)} albums")
        logger.debug(f"Album list response: {json.dumps(results, indent=2)}")
        return albums
    except HttpError as error:
        logger.error(f"Error listing albums: {error}")
        return []

def list_media_items_in_album(album_id):
    """List all media items in a specific album."""
    service = get_photos_session()
    if not service:
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
        return []

def get_random_photo_batch():
    """Get a random batch of photos from a random album."""
    service = get_photos_session()
    if not service:
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
        
        return selected_photos
    
    except Exception as e:
        logger.error(f"Error getting random photo batch: {e}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        return []

def api_data():
    """API endpoint for getting photo data."""
    try:
        photos = get_random_photo_batch()
        if not photos:
            logger.warning("No photos returned from get_random_photo_batch")
            return {'error': 'No photos available'}
        
        logger.info(f"Returning {len(photos)} photos")
        return {'photos': photos}
    except Exception as e:
        logger.error(f"Error in api_data: {e}")
        logger.debug(f"API error traceback: {traceback.format_exc()}")
        return {'error': str(e)}

def init(config):
    logger.info("Initializing Google Photos plugin")
    logger.debug(f"Config: {json.dumps(config, indent=2)}")
    ensure_cache_dir()
    return {"data": {}} 