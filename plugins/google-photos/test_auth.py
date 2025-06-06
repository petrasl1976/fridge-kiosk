#!/usr/bin/env python3
"""
Test Google Photos Authentication
Simple test to verify credentials and scopes are working correctly.
"""

import os
import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_photos_auth():
    """Test Google Photos authentication and API access."""
    print("🔍 Testing Google Photos Authentication")
    print("=" * 50)
    
    # Load token directly
    token_path = project_root / 'config' / 'token.json'
    print(f"📁 Token path: {token_path}")
    
    if not token_path.exists():
        print("❌ token.json not found!")
        return False
    
    # Load and display token info
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    print(f"🔑 Token scopes:")
    for scope in token_data.get('scopes', []):
        print(f"   - {scope}")
    
    print(f"📅 Token expired: {token_data.get('expired', 'Unknown')}")
    
    # Create credentials
    try:
        credentials = Credentials(**token_data)
        print(f"✅ Credentials created successfully")
        print(f"   - Expired: {credentials.expired}")
        print(f"   - Has refresh token: {bool(credentials.refresh_token)}")
        print(f"   - Scopes: {credentials.scopes}")
    except Exception as e:
        print(f"❌ Error creating credentials: {e}")
        return False
    
    # Test Photos API service creation
    try:
        print(f"\n📡 Testing Photos API service creation...")
        service = build(
            'photoslibrary', 'v1', 
            credentials=credentials,
            discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1'
        )
        print(f"✅ Photos API service created successfully")
        
        # Test simple API call
        print(f"\n📸 Testing simple API call (list albums)...")
        results = service.albums().list(pageSize=5).execute()
        albums = results.get('albums', [])
        print(f"✅ Successfully retrieved {len(albums)} albums")
        
        for i, album in enumerate(albums[:3]):
            title = album.get('title', 'Unnamed')
            count = album.get('mediaItemsCount', 0)
            print(f"   {i+1}. {title} ({count} items)")
        
        # Test media items access
        if albums:
            print(f"\n🖼️  Testing media items access...")
            test_album = albums[0]
            album_id = test_album['id']
            album_title = test_album.get('title', 'Unnamed')
            
            body = {"albumId": album_id, "pageSize": 5}
            media_results = service.mediaItems().search(body=body).execute()
            media_items = media_results.get('mediaItems', [])
            
            print(f"✅ Successfully accessed {len(media_items)} media items from '{album_title}'")
            
            for i, item in enumerate(media_items[:2]):
                filename = item.get('filename', 'Unknown')
                mime_type = item.get('mimeType', 'Unknown')
                print(f"   {i+1}. {filename} ({mime_type})")
        
        return True
        
    except Exception as e:
        print(f"❌ Photos API test failed: {e}")
        print(f"   Error details: {str(e)}")
        
        # Check for specific scope errors
        error_str = str(e).lower()
        if "insufficient authentication scopes" in error_str:
            print(f"\n💡 DIAGNOSIS: Scope issue detected!")
            print(f"   This means the credentials don't have the Photos Library scope.")
            print(f"   Even though the token.json contains the scope, the actual")
            print(f"   credentials being used by the API don't have it.")
            print(f"\n🔧 Try these fixes:")
            print(f"   1. Delete token.json and re-authenticate")
            print(f"   2. Make sure the app is published in Google Cloud Console")
            print(f"   3. Clear browser cache and Google account permissions")
        
        return False

if __name__ == '__main__':
    success = test_photos_auth()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}") 