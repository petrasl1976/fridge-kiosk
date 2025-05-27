import os
import json
import logging
import random
import requests
import time
from google.oauth2.credentials import Credentials

# Use a named logger for this plugin
logger = logging.getLogger("google_photos_plugin")
logger.setLevel(logging.DEBUG)

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
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'token.json')
    token_path = os.path.abspath(token_path)
    logger.debug(f"Looking for token.json at: {token_path}")
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r') as token_file:
                token_data = json.load(token_file)
                logger.info("Loaded token.json successfully.")
                return Credentials(**token_data)
        except Exception as e:
            logger.error(f"Failed to load token.json: {e}")
    else:
        logger.warning("token.json not found!")
    return None

def get_photos_session(creds):
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {creds.token}',
        'Content-type': 'application/json'
    })
    logger.debug(f"Created requests session with token: {creds.token[:8]}... (truncated)")
    return session

def list_albums(creds, page_size=50):
    logger.info("Listing albums from Google Photos API...")
    session = get_photos_session(creds)
    url = f'https://photoslibrary.googleapis.com/v1/albums?pageSize={page_size}'
    try:
        response = session.get(url)
        logger.debug(f"Albums API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            albums = data.get('albums', [])
            logger.info(f"Found {len(albums)} albums.")
            return albums
        else:
            logger.error(f"Error listing albums: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Exception in list_albums: {e}")
        return []

def get_all_media_items(creds, album_id):
    logger.info(f"Getting all media items for album: {album_id}")
    session = get_photos_session(creds)
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    items = []
    next_page_token = None
    
    while True:
        body = {
            "albumId": album_id,
            "pageSize": 100,
            "pageToken": next_page_token
        }
        try:
            response = session.post(url, json=body)
            if response.status_code == 200:
                data = response.json()
                found_items = data.get('mediaItems', [])
                items.extend(found_items)
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
            else:
                logger.error(f"Error getting media items: {response.text}")
                break
        except Exception as e:
            logger.error(f"Exception getting media items: {e}")
            break
    
    logger.info(f"Found {len(items)} total media items in album {album_id}")
    return items

def get_random_photo_batch(creds, batch_size=5):
    logger.info(f"Selecting random photo batch (batch_size={batch_size})...")
    
    # Try to load from cache first
    cache = load_cache()
    if cache and 'albums' in cache:
        albums = cache['albums']
    else:
        # If no cache or expired, fetch from API
        albums = list_albums(creds)
        if albums:
            # Save album list to cache
            save_cache({'albums': albums})
    
    if not albums:
        logger.error("No albums found")
        return []
    
    # Shuffle albums in random order
    random.shuffle(albums)
    
    # Try all albums until we find a suitable one
    for album_attempt in range(len(albums)):
        album = albums[album_attempt]
        album_title = album.get('title', 'Unknown Album')
        logger.info(f"Trying album: {album_title} (attempt {album_attempt+1}/{len(albums)})")
        
        try:
            items = get_all_media_items(creds, album['id'])
            if not items:
                logger.info(f"Album {album_title} has no items, skipping")
                continue

            # Filter only those that have creationTime
            items = [i for i in items if i.get('mediaMetadata', {}).get('creationTime')]
            if not items:
                logger.info(f"Album {album_title} has no items with creationTime, skipping")
                continue

            # Process items and add metadata
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
                    'mimeType': item.get('mimeType', ''),
                    'videoMetadata': video_metadata,
                    'albumTitle': album_title
                })
            
            if processed_items:
                logger.info(f"Album {album_title} has {len(processed_items)} items")
                
                # Sort by creationTime
                processed_items.sort(key=lambda x: x['photo_time'])
                total = len(processed_items)
                start_index = random.randint(0, total - 1)
                batch = []
                
                # Collect batch
                count = min(batch_size, total)
                for i in range(count):
                    idx = (start_index + i) % total
                    batch.append(processed_items[idx])
                
                logger.info(f"Returning batch with {len(batch)} items.")
                return batch
            else:
                logger.info(f"Album {album_title} has no suitable items, skipping")
                
        except Exception as e:
            logger.error(f"Error processing album {album_title}: {e}")
            if hasattr(e, 'resp') and e.resp.status == 429:
                logger.warning("Google Photos API quota exceeded")
                return [{"error": "Google Photos API quota exceeded", "mimeType": "error"}]
    
    logger.error("No suitable media found in any album")
    return [{"error": "No suitable media found", "mimeType": "error"}]

def api_data():
    logger.info("api_data called for Google Photos plugin")
    creds = get_credentials()
    if not creds:
        logger.error("No credentials returned from get_credentials()")
        return {"error": "No credentials"}
    
    batch = get_random_photo_batch(creds, batch_size=5)
    logger.info(f"Returning batch with {len(batch)} items.")
    return {"media": batch}

def init(config):
    logger.info("Initializing Google Photos plugin")
    logger.debug(f"Config: {json.dumps(config, indent=2)}")
    ensure_cache_dir()
    return {"data": {}} 