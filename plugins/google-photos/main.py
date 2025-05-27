import os
import json
import logging
import random
import requests
from google.oauth2.credentials import Credentials

def get_credentials():
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config', 'token.json')
    token_path = os.path.abspath(token_path)
    if os.path.exists(token_path):
        with open(token_path, 'r') as token_file:
            token_data = json.load(token_file)
            return Credentials(**token_data)
    return None

def get_photos_session(creds):
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {creds.token}',
        'Content-type': 'application/json'
    })
    return session

def list_albums(creds, page_size=50):
    session = get_photos_session(creds)
    url = f'https://photoslibrary.googleapis.com/v1/albums?pageSize={page_size}'
    response = session.get(url)
    if response.status_code == 200:
        return response.json().get('albums', [])
    else:
        logging.error(f"Error listing albums: {response.text}")
        return []

def list_media_items_in_album(creds, album_id, page_size=100):
    session = get_photos_session(creds)
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    body = {
        "albumId": album_id,
        "pageSize": page_size
    }
    response = session.post(url, json=body)
    if response.status_code == 200:
        return response.json().get('mediaItems', [])
    else:
        logging.error(f"Error listing media items: {response.text}")
        return []

def get_random_photo_batch(creds, batch_size=5):
    albums = list_albums(creds)
    if not albums:
        logging.error("No albums found")
        return []
    album = random.choice(albums)
    album_id = album['id']
    album_title = album.get('title', 'Unknown Album')
    media_items = list_media_items_in_album(creds, album_id)
    if not media_items:
        logging.error(f"No media items found in album {album_title}")
        return []
    if len(media_items) <= batch_size:
        start_idx = 0
    else:
        start_idx = random.randint(0, len(media_items) - batch_size)
    batch = media_items[start_idx:start_idx + batch_size]
    logging.info(f"Selected album: {album_title}, batch from {start_idx}, batch size: {len(batch)}")
    # Add album info to each item for frontend
    for item in batch:
        item['albumTitle'] = album_title
    return batch

def api_data():
    creds = get_credentials()
    if not creds:
        logging.error("No credentials returned from get_credentials()")
        return {"error": "No credentials"}
    batch = get_random_photo_batch(creds, batch_size=5)
    return {"media": batch}

def init(config):
    """Initialize the plugin"""
    return {"data": {}} 