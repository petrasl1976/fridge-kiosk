#!/usr/bin/env python3
"""
Final debug script for Google Photos API after successful OAuth
"""

import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

def test_api():
    print("🔍 Final Google Photos API Test")
    print("=" * 50)
    
    # Load fresh token
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    print(f"📁 Token path: {token_path}")
    
    if not token_path.exists():
        print("❌ token.json not found!")
        return False
    
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    print(f"🔑 Token scopes: {token_data.get('scopes', [])}")
    print(f"📅 Token expires: {token_data.get('expiry', 'No expiry info')}")
    
    # Create credentials
    try:
        credentials = Credentials(**token_data)
        print(f"✅ Credentials created")
        print(f"   - Expired: {credentials.expired}")
        print(f"   - Valid: {credentials.valid}")
        
        # Test raw token with Photos API
        print(f"\n🌐 Testing raw HTTP request to Photos API...")
        headers = {'Authorization': f'Bearer {credentials.token}'}
        
        # Test simple albums endpoint
        url = 'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'
        response = requests.get(url, headers=headers)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Raw HTTP request SUCCESS!")
            data = response.json()
            albums = data.get('albums', [])
            print(f"   Found {len(albums)} albums")
        else:
            print(f"   ❌ Raw HTTP request FAILED")
            print(f"   Response: {response.text}")
            
        # Test with google client library
        print(f"\n📚 Testing with Google Client Library...")
        try:
            service = build('photoslibrary', 'v1', credentials=credentials,
                           discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
            print(f"   Service created successfully")
            
            results = service.albums().list(pageSize=1).execute()
            albums = results.get('albums', [])
            print(f"   ✅ Client library SUCCESS! Found {len(albums)} albums")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Client library FAILED: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = test_api()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}") 