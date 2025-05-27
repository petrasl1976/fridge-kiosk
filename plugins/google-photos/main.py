import os
import json
import logging
import random
import requests
from google.oauth2.credentials import Credentials

# Use a named logger for this plugin
logger = logging.getLogger("google_photos_plugin")
logger.setLevel(logging.DEBUG)

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
        logger.debug(f"Albums API response headers: {dict(response.headers)}")
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Albums API response data: {json.dumps(data, indent=2)}")
            albums = data.get('albums', [])
            logger.info(f"Found {len(albums)} albums.")
            return albums
        else:
            logger.error(f"Error listing albums: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Exception in list_albums: {e}")
        return []

def list_media_items_in_album(creds, album_id, page_size=100):
    logger.info(f"Listing media items for album: {album_id}")
    session = get_photos_session(creds)
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    body = {
        "albumId": album_id,
        "pageSize": page_size
    }
    try:
        response = session.post(url, json=body)
        logger.debug(f"MediaItems API response status: {response.status_code}")
        logger.debug(f"MediaItems API response headers: {dict(response.headers)}")
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"MediaItems API response data: {json.dumps(data, indent=2)}")
            items = data.get('mediaItems', [])
            logger.info(f"Found {len(items)} media items in album {album_id}.")
            return items
        else:
            logger.error(f"Error listing media items: {response.text}")
            return []
    except Exception as e:
        logger.error(f"Exception in list_media_items_in_album: {e}")
        return []

def get_random_photo_batch(creds, batch_size=5):
    logger.info(f"Selecting random photo batch (batch_size={batch_size})...")
    albums = list_albums(creds)
    if not albums:
        logger.error("No albums found")
        return []
    
    # Filter out empty albums
    non_empty_albums = []
    for album in albums:
        media_items = list_media_items_in_album(creds, album['id'])
        if media_items:
            non_empty_albums.append(album)
    
    if not non_empty_albums:
        logger.error("No non-empty albums found")
        return []
    
    album = random.choice(non_empty_albums)
    album_id = album['id']
    album_title = album.get('title', 'Unknown Album')
    logger.info(f"Selected album: {album_title} (ID: {album_id})")
    
    media_items = list_media_items_in_album(creds, album_id)
    if not media_items:
        logger.error(f"No media items found in album {album_title}")
        return []
    
    logger.info(f"Total media items in album: {len(media_items)}")
    if len(media_items) <= batch_size:
        start_idx = 0
    else:
        start_idx = random.randint(0, len(media_items) - batch_size)
    
    batch = media_items[start_idx:start_idx + batch_size]
    logger.info(f"Selected batch from index {start_idx}, batch size: {len(batch)}")
    
    # Add album info to each item for frontend
    for item in batch:
        item['albumTitle'] = album_title
        logger.debug(f"Media item: {json.dumps(item, indent=2)}")
    
    return batch

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
    return {"data": {}} 