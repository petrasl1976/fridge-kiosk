import os
import json
import random
import logging
from pathlib import Path
import google.oauth2.credentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
TOKEN_FILE = PROJECT_ROOT / 'config' / 'token.json'

# Configure logging
logger = logging.getLogger(__name__)

# Cache settings
ALBUMS_CACHE_FILE = PROJECT_ROOT / 'config' / 'albums_cache.json'
CACHE_EXPIRATION = 30 * 24 * 3600  # 30 days

def get_credentials():
    """Get credentials for Google Photos API"""
    if not TOKEN_FILE.exists():
        logger.error("No token file found")
        return None
        
    try:
        with open(TOKEN_FILE, 'r') as token:
            creds_data = json.load(token)
            creds = Credentials.from_authorized_user_info(creds_data)
            
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                
        return creds
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

def load_album_cache():
    """Load albums from cache if it exists and is not expired"""
    if not ALBUMS_CACHE_FILE.exists():
        return None
        
    try:
        with open(ALBUMS_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            if cache_data.get('timestamp', 0) + CACHE_EXPIRATION > time.time():
                return cache_data.get('albums')
    except Exception as e:
        logger.error(f"Error loading album cache: {e}")
    return None

def save_album_cache(albums):
    """Save albums to cache"""
    try:
        with open(ALBUMS_CACHE_FILE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'albums': albums
            }, f)
    except Exception as e:
        logger.error(f"Error saving album cache: {e}")

def get_all_albums(photos_service):
    """Get all albums from Google Photos"""
    albums = load_album_cache()
    if albums:
        return albums

    albums = []
    next_page_token = None
    while True:
        resp = photos_service.albums().list(pageSize=50, pageToken=next_page_token).execute()
        found_albums = resp.get('albums', [])
        albums.extend(found_albums)
        next_page_token = resp.get('nextPageToken')
        if not next_page_token:
            break

    save_album_cache(albums)
    return albums

def get_all_media_items(photos_service, album_id):
    """Get all media items from an album"""
    items = []
    next_page_token = None
    while True:
        resp = photos_service.mediaItems().search(
            body={'albumId': album_id, 'pageSize': 100, 'pageToken': next_page_token}
        ).execute()
        found_items = resp.get('mediaItems', [])
        items.extend(found_items)
        next_page_token = resp.get('nextPageToken')
        if not next_page_token:
            break
    return items

def get_random_photo_batch(photos_service):
    """Get a random batch of photos from a random album"""
    try:
        albums = get_all_albums(photos_service)
        if not albums:
            logger.warning("No albums found")
            return [{"error": "No albums found"}], "Error"
        
        # Shuffle albums in random order
        random.shuffle(albums)
        
        # Try all albums until we find a suitable one
        for album_attempt in range(len(albums)):
            album = albums[album_attempt]
            album_title = album.get('title', 'Unknown Album')
            logger.info(f"Trying album: {album_title} (attempt {album_attempt+1}/{len(albums)})")
            
            try:
                items = get_all_media_items(photos_service, album['id'])
                if not items:
                    logger.info(f"Album {album_title} has no items, skipping")
                    continue

                # Filter only those that have creationTime
                items = [i for i in items if i.get('mediaMetadata', {}).get('creationTime')]
                if not items:
                    logger.info(f"Album {album_title} has no items with creationTime, skipping")
                    continue

                # Process items
                processed_items = []
                for item in items:
                    meta = item.get('mediaMetadata', {})
                    media_type = "photo"
                    video_metadata = {}
                    
                    if 'video' in meta:
                        media_type = "video"
                        video_metadata = meta.get('video', {})
                    
                    processed_items.append({
                        'baseUrl': item.get('baseUrl', ''),
                        'photo_time': meta.get('creationTime', ''),
                        'filename': item.get('filename', 'Unknown'),
                        'mediaType': media_type,
                        'videoMetadata': video_metadata,
                        'mimeType': item.get('mimeType', '')
                    })
                
                if processed_items:
                    logger.info(f"Album {album_title} has {len(processed_items)} items")
                    
                    # Sort by creationTime
                    processed_items.sort(key=lambda x: x['photo_time'])
                    total = len(processed_items)
                    start_index = random.randint(0, total - 1)
                    batch = []
                    
                    # Get batch of items
                    count = min(5, total)  # Default batch size of 5
                    for i in range(count):
                        idx = (start_index + i) % total
                        batch.append(processed_items[idx])

                    return batch, album_title
                else:
                    logger.info(f"Album {album_title} has no matching items, skipping")
            except Exception as e:
                logger.error(f"Error processing album {album_title}: {e}")
                if "quota" in str(e).lower():
                    return [{"error": "Google Photos API quota exceeded", "mediaType": "error"}], "API Limit Error"

    except Exception as e:
        logger.error(f"Unexpected error in get_random_photo_batch: {e}")
        return [{"error": str(e), "mediaType": "error"}], "Error"
    
    return [{"error": "No suitable media found", "mediaType": "error"}], "No Media"

def api_data():
    """API handler for /api/plugins/google-photos/data"""
    creds = get_credentials()
    if not creds:
        return {"error": "Not authenticated"}

    try:
        photos_service = build('photoslibrary', 'v1', credentials=creds)
        photo_batch, album_title = get_random_photo_batch(photos_service)
        
        if not photo_batch:
            return {"error": "No photos found", "photos": [{"error": "No photos found", "mediaType": "error"}]}
        
        if 'error' in photo_batch[0]:
            return {"error": photo_batch[0]['error'], "photos": photo_batch, "album_title": album_title}
            
        return {"photos": photo_batch, "album_title": album_title}
        
    except Exception as e:
        logger.error(f"Error in api_data: {e}")
        return {"error": str(e), "photos": [{"error": str(e), "mediaType": "error"}], "album_title": "Error"}

def init(config):
    """Initialize the plugin"""
    return {"data": {}} 