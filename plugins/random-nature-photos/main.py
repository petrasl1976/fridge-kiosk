#!/usr/bin/env python3
"""
Random Nature Photos Plugin
===========================

Fetches beautiful nature photos from Unsplash API and displays them in a slideshow.
No authentication required - uses Unsplash's free public API.
"""

import os
import json
import time
import random
import logging
import requests
from pathlib import Path
from PIL import Image
import hashlib

def get_plugin_path():
    """Get the path to this plugin directory"""
    return Path(__file__).parent

def get_data_path():
    """Get the path to the plugin's data directory"""
    return get_plugin_path() / 'data'

def load_config():
    """Load plugin configuration"""
    config_path = get_plugin_path() / 'config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        return {}

def get_cache_file():
    """Get path to the cache file"""
    return get_data_path() / 'photo_cache.json'

def load_cache():
    """Load cached photo data"""
    cache_file = get_cache_file()
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading cache: {e}")
    
    return {
        'photos': [],
        'last_updated': 0,
        'current_index': 0
    }

def save_cache(cache_data):
    """Save cache data to file"""
    cache_file = get_cache_file()
    try:
        get_data_path().mkdir(exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving cache: {e}")

def should_refresh_photos(config, cache_data):
    """Check if we need to refresh photos from API"""
    if not cache_data.get('photos'):
        return True
    
    refresh_interval = config.get('unsplash', {}).get('refreshInterval', 3600)
    last_updated = cache_data.get('last_updated', 0)
    
    return (time.time() - last_updated) > refresh_interval

def get_unsplash_photos(config):
    """Fetch photos from Unsplash API"""
    unsplash_config = config.get('unsplash', {})
    categories = unsplash_config.get('categories', ['nature'])
    photos_per_batch = unsplash_config.get('photosPerBatch', 20)
    orientation = unsplash_config.get('orientation', 'landscape')
    api_key = unsplash_config.get('apiKey', '')
    
    all_photos = []
    
    # If no API key, return fallback photos
    if not api_key:
        logging.warning("No Unsplash API key configured, using fallback photos")
        return get_fallback_photos()
    
    for category in categories:
        try:
            # Unsplash API endpoint with proper authentication
            url = "https://api.unsplash.com/search/photos"
            params = {
                'query': category,
                'per_page': photos_per_batch // len(categories),
                'orientation': orientation,
                'order_by': 'relevant'
            }
            
            headers = {
                'Authorization': f'Client-ID {api_key}',
                'Accept-Version': 'v1'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                photos = data.get('results', [])
                
                for photo in photos:
                    photo_info = {
                        'id': photo['id'],
                        'url': photo['urls']['regular'],  # Good quality for displays
                        'thumb_url': photo['urls']['thumb'],
                        'description': photo.get('description', '') or photo.get('alt_description', ''),
                        'photographer': photo['user']['name'],
                        'category': category,
                        'width': photo['width'],
                        'height': photo['height'],
                        'download_url': photo['links']['download_location']
                    }
                    all_photos.append(photo_info)
                    
                logging.info(f"Fetched {len(photos)} photos for category: {category}")
                
            elif response.status_code == 401:
                logging.error(f"Unauthorized access to Unsplash API. Check your API key.")
                return get_fallback_photos()
            elif response.status_code == 403:
                logging.error(f"Rate limit exceeded for Unsplash API")
                return get_fallback_photos() 
            else:
                logging.warning(f"Failed to fetch photos for {category}: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Error fetching photos for {category}: {e}")
    
    if not all_photos:
        logging.warning("No photos fetched from Unsplash, using fallback photos")
        return get_fallback_photos()
    
    # Shuffle for variety
    random.shuffle(all_photos)
    logging.info(f"Total photos fetched: {len(all_photos)}")
    
    return all_photos

def get_fallback_photos():
    """Provide beautiful fallback photos when API is unavailable"""
    # High quality nature photos that work without API
    fallback_photos = [
        {
            'id': 'fallback_1',
            'url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400&q=80',
            'description': 'Mountain landscape with clouds',
            'photographer': 'Unsplash',
            'category': 'nature',
            'width': 1920,
            'height': 1080
        },
        {
            'id': 'fallback_2', 
            'url': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&q=80',
            'description': 'Forest path in autumn',
            'photographer': 'Unsplash',
            'category': 'forest',
            'width': 1920,
            'height': 1080
        },
        {
            'id': 'fallback_3',
            'url': 'https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=400&q=80',
            'description': 'Lake with mountain reflections',
            'photographer': 'Unsplash',
            'category': 'landscape',
            'width': 1920,
            'height': 1080
        },
        {
            'id': 'fallback_4',
            'url': 'https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=400&q=80',
            'description': 'Ocean waves on sandy beach',
            'photographer': 'Unsplash',
            'category': 'ocean',
            'width': 1920,
            'height': 1080
        },
        {
            'id': 'fallback_5',
            'url': 'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=400&q=80',
            'description': 'Sunset over mountain peaks',
            'photographer': 'Unsplash',
            'category': 'mountains',
            'width': 1920,
            'height': 1080
        },
        {
            'id': 'fallback_6',
            'url': 'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1920&q=80',
            'thumb_url': 'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=400&q=80',
            'description': 'Dramatic sky with clouds',
            'photographer': 'Unsplash',
            'category': 'sky',
            'width': 1920,
            'height': 1080
        }
    ]
    
    logging.info(f"Using {len(fallback_photos)} fallback photos")
    return fallback_photos

def get_current_photo(config):
    """Get the current photo to display"""
    cache_data = load_cache()
    
    # Check if we need to refresh photos
    if should_refresh_photos(config, cache_data):
        logging.info("Refreshing photos from Unsplash...")
        try:
            new_photos = get_unsplash_photos(config)
            if new_photos:
                cache_data['photos'] = new_photos
                cache_data['last_updated'] = time.time()
                cache_data['current_index'] = 0
                cache_data['last_photo_change'] = 0  # Reset photo change timer
                save_cache(cache_data)
                logging.info(f"Cache updated with {len(new_photos)} photos")
        except Exception as e:
            logging.error(f"Failed to refresh photos: {e}")
    
    # Get current photo
    photos = cache_data.get('photos', [])
    if not photos:
        return {
            'error': 'No photos available',
            'message': 'Failed to load photos from Unsplash'
        }
    
    current_index = cache_data.get('current_index', 0)
    last_photo_change = cache_data.get('last_photo_change', 0)
    
    # Only advance to next photo if enough time has passed
    slideshow_config = config.get('slideshow', {})
    display_duration = slideshow_config.get('displayDuration', 15)  # seconds
    
    current_time = time.time()
    
    # Check if it's time to change photo
    if current_time - last_photo_change >= display_duration:
        # Move to next photo
        next_index = (current_index + 1) % len(photos)
        cache_data['current_index'] = next_index
        cache_data['last_photo_change'] = current_time
        save_cache(cache_data)
        current_index = next_index
        logging.info(f"Advanced to photo {current_index + 1}/{len(photos)} after {display_duration}s")
    else:
        # Still showing the same photo
        time_remaining = display_duration - (current_time - last_photo_change)
        logging.debug(f"Still showing photo {current_index + 1}/{len(photos)}, {time_remaining:.1f}s remaining")
    
    current_photo = photos[current_index]
    
    return {
        'photo': current_photo,
        'current_index': current_index + 1,
        'total_photos': len(photos),
        'next_refresh': cache_data['last_updated'] + config.get('unsplash', {}).get('refreshInterval', 3600),
        'time_remaining': display_duration - (current_time - last_photo_change)
    }

def api_data():
    """API endpoint to get current photo data"""
    config = load_config()
    return get_current_photo(config)

def api_next():
    """API endpoint to manually get next photo"""
    config = load_config()
    return get_current_photo(config)

def api_refresh():
    """API endpoint to force refresh photos from API"""
    config = load_config()
    cache_data = load_cache()
    
    try:
        new_photos = get_unsplash_photos(config)
        if new_photos:
            cache_data['photos'] = new_photos
            cache_data['last_updated'] = time.time()
            cache_data['current_index'] = 0
            save_cache(cache_data)
            
            return {
                'success': True,
                'message': f'Refreshed {len(new_photos)} photos',
                'photos_count': len(new_photos)
            }
        else:
            return {
                'success': False,
                'message': 'No photos fetched from API'
            }
    except Exception as e:
        logging.error(f"Error in api_refresh: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

def init(config):
    """Initialize the plugin"""
    logging.info("Initializing Random Nature Photos plugin")
    
    # Ensure data directory exists
    get_data_path().mkdir(exist_ok=True)
    
    # Load initial photo
    initial_data = get_current_photo(config)
    
    return {
        'status': 'initialized',
        'data': initial_data,
        'plugin_info': {
            'name': config.get('name', 'Random Nature Photos'),
            'version': config.get('version', '1.0.0'),
            'description': config.get('description', 'Beautiful nature photos from Unsplash')
        }
    } 