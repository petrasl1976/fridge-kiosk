import os
import json
import time
import random
import logging
from datetime import datetime
import google.oauth2.credentials
import googleapiclient.discovery
from flask import jsonify, session

# Configure logger
logger = logging.getLogger(__name__)

class GooglePhotosPlugin:
    def __init__(self, config):
        self.config = config
        self.albums_cache_file = os.path.join(os.path.dirname(__file__), 'albums_cache.json')
        self.cache_expiration = 30 * 24 * 3600  # 30 days

    def load_album_cache(self):
        try:
            with open(self.albums_cache_file, 'r') as f:
                cache = json.load(f)
                age = time.time() - cache.get('timestamp', 0)
                if age < self.cache_expiration:
                    return cache.get('albums', [])
        except:
            pass
        return []

    def save_album_cache(self, albums):
        cache = {
            'timestamp': time.time(),
            'albums': albums
        }
        try:
            with open(self.albums_cache_file, 'w') as f:
                json.dump(cache, f)
        except:
            pass

    def get_all_albums(self, photos_service):
        albums = self.load_album_cache()
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

        self.save_album_cache(albums)
        return albums

    def get_all_media_items(self, photos_service, album_id):
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

    def get_random_photo_batch(self, photos_service):
        try:
            albums = self.get_all_albums(photos_service)
            if not albums:
                logger.warning("No albums found.")
                return [{"error": "No albums found"}], "Error"
            
            # Shuffle albums in random order
            random.shuffle(albums)
            
            # Try all albums until we find a suitable one
            for album_attempt in range(len(albums)):
                album = albums[album_attempt]
                album_title = album.get('title', 'Unknown Album')
                logger.info(f"Trying album: {album_title} (attempt {album_attempt+1}/{len(albums)})")
                
                try:
                    items = self.get_all_media_items(photos_service, album['id'])
                    if not items:
                        logger.info(f"Album {album_title} has no items, skipping")
                        continue

                    # Filter only those that have creationTime
                    items = [i for i in items if i.get('mediaMetadata', {}).get('creationTime')]
                    if not items:
                        logger.info(f"Album {album_title} has no items with creationTime, skipping")
                        continue

                    # Identify media types and filter according to MEDIA_TYPES setting
                    processed_items = []
                    for item in items:
                        meta = item.get('mediaMetadata', {})
                        # Determine media type and add additional metadata
                        media_type = "photo"
                        video_metadata = {}
                        
                        if 'video' in meta:
                            media_type = "video"
                            video_metadata = meta.get('video', {})
                        
                        # Filter by configured media type
                        if self.config.MEDIA_TYPES.lower() == "all" or self.config.MEDIA_TYPES.lower() == media_type:
                            processed_items.append({
                                'baseUrl': item.get('baseUrl', ''),
                                'photo_time': meta.get('creationTime', ''),
                                'filename': item.get('filename', 'Unknown'),
                                'mediaType': media_type,
                                'videoMetadata': video_metadata,
                                'mimeType': item.get('mimeType', '')
                            })
                    
                    # If this album has suitable media, use it
                    if processed_items:
                        logger.info(f"Album {album_title} has {len(processed_items)} matching items of type {self.config.MEDIA_TYPES}")
                        
                        # Sort by creationTime
                        processed_items.sort(key=lambda x: x['photo_time'])
                        
                        # Return a batch of photos
                        return processed_items, album_title
                        
                except Exception as e:
                    logger.error(f"Error processing album {album_title}: {e}")
                    continue
            
            # If we get here, no suitable album was found
            return [{"error": "No suitable albums found"}], "Error"
            
        except Exception as e:
            logger.error(f"Error in get_random_photo_batch: {e}")
            return [{"error": str(e)}], "Error"

    def get_photos(self, credentials):
        try:
            photos_service = googleapiclient.discovery.build(
                'photoslibrary', 'v1', credentials=credentials,
                discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
            )
            
            photo_batch, album_title = self.get_random_photo_batch(photos_service)
            
            # Check if we have an error message
            if photo_batch and len(photo_batch) > 0 and 'error' in photo_batch[0]:
                return {"error": photo_batch[0]['error'], "photos": photo_batch, "album_title": album_title}
                
            # Log the first photo/video in the batch that will be displayed
            if photo_batch and len(photo_batch) > 0:
                first_item = photo_batch[0]
                media_type = first_item.get('mediaType', 'unknown')
                filename = first_item.get('filename', 'unknown')
                logger.info(f"[{album_title}] {filename} ({media_type})")
                
            return {"photos": photo_batch, "album_title": album_title}
            
        except Exception as e:
            logger.error(f"Error getting photos: {e}")
            return {"error": str(e), "photos": [{"error": str(e), "mediaType": "error"}], "album_title": "Error"}

def init_plugin(app, config):
    plugin = GooglePhotosPlugin(config)
    
    @app.route('/api/plugins/google-photos/data')
    def new_photo():
        """Returns a new batch of photos in JSON format"""
        try:
            if 'credentials' not in session:
                return jsonify({"error": "Not authenticated"}), 401
                
            # Load credentials from the session
            creds = google.oauth2.credentials.Credentials(**session['credentials'])
            
            # Get photos using the plugin
            result = plugin.get_photos(creds)
            
            # If there's an error, return it with 200 status so frontend can handle it
            if 'error' in result:
                return jsonify(result)
                
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e), "photos": [{"error": str(e), "mediaType": "error"}], "album_title": "Error"})

def api_data():
    """API endpoint for getting photos data"""
    try:
        if 'credentials' not in session:
            return {"error": "Not authenticated", "mediaItems": []}
            
        # Load credentials from the session
        creds = google.oauth2.credentials.Credentials(**session['credentials'])
        
        # Get photos using the plugin
        result = GooglePhotosPlugin(config).get_photos(creds)
        
        # Format the response
        if 'error' in result:
            return {"error": result['error'], "mediaItems": []}
            
        return {
            "mediaItems": result['photos'],
            "albumTitle": result['album_title']
        }
        
    except Exception as e:
        return {"error": str(e), "mediaItems": []} 