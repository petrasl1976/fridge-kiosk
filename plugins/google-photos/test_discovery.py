#!/usr/bin/env python3
"""
Test Google Photos API with different discovery URLs
"""

import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def test_different_discovery():
    print("🔬 Testing different discovery URLs...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    credentials = Credentials(**token_data)
    
    # Different discovery URLs to try
    discovery_urls = [
        'https://photoslibrary.googleapis.com/$discovery/rest?version=v1',  # Current
        None,  # Default discovery
        'https://www.googleapis.com/discovery/v1/apis/photoslibrary/v1/rest',  # Alternative
    ]
    
    for i, discovery_url in enumerate(discovery_urls):
        print(f"\n📡 Test {i+1}: {discovery_url or 'Default discovery'}")
        
        try:
            if discovery_url:
                service = build('photoslibrary', 'v1', credentials=credentials,
                              discoveryServiceUrl=discovery_url)
            else:
                service = build('photoslibrary', 'v1', credentials=credentials)
            
            print("   Service created successfully")
            
            # Try to list albums
            results = service.albums().list(pageSize=1).execute()
            albums = results.get('albums', [])
            print(f"   ✅ SUCCESS! Found {len(albums)} albums")
            return True
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    return False

def test_shared_albums():
    """Test shared albums instead of regular albums"""
    print("\n📸 Testing shared albums...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    credentials = Credentials(**token_data)
    
    try:
        service = build('photoslibrary', 'v1', credentials=credentials,
                       discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        
        # Try shared albums
        results = service.sharedAlbums().list(pageSize=1).execute()
        shared_albums = results.get('sharedAlbums', [])
        print(f"   ✅ Shared albums SUCCESS! Found {len(shared_albums)} shared albums")
        return True
        
    except Exception as e:
        print(f"   ❌ Shared albums failed: {e}")
        return False

def test_media_search():
    """Test direct media search without album"""
    print("\n🖼️  Testing direct media search...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    credentials = Credentials(**token_data)
    
    try:
        service = build('photoslibrary', 'v1', credentials=credentials,
                       discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        
        # Try direct media search
        body = {"pageSize": 1}
        results = service.mediaItems().search(body=body).execute()
        media_items = results.get('mediaItems', [])
        print(f"   ✅ Media search SUCCESS! Found {len(media_items)} media items")
        return True
        
    except Exception as e:
        print(f"   ❌ Media search failed: {e}")
        return False

def main():
    print("🔬 Comprehensive Google Photos API Testing")
    print("=" * 50)
    
    # Test different discovery methods
    success1 = test_different_discovery()
    
    # Test alternative endpoints
    success2 = test_shared_albums()
    success3 = test_media_search()
    
    overall_success = success1 or success2 or success3
    print(f"\n{'✅ SUCCESS' if overall_success else '❌ FAILED'}")

if __name__ == '__main__':
    main() 