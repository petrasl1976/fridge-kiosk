#!/usr/bin/env python3
"""
Deep token debugging for Google Photos API
"""

import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

def debug_token():
    print("🔍 Deep Token Analysis")
    print("=" * 50)
    
    # Load token
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    print("📋 Raw Token Data:")
    for key, value in token_data.items():
        if key == 'token':
            print(f"   {key}: {value[:20]}...{value[-10:]} (truncated)")
        elif key == 'refresh_token':
            print(f"   {key}: {value[:20]}...{value[-10:]} (truncated)")
        elif key == 'client_secret':
            print(f"   {key}: {value[:10]}... (truncated)")
        else:
            print(f"   {key}: {value}")
    
    # Create credentials
    credentials = Credentials(**token_data)
    
    print(f"\n🔑 Credentials Object:")
    print(f"   Expired: {credentials.expired}")
    print(f"   Token: {credentials.token[:20]}...{credentials.token[-10:] if credentials.token else 'None'}")
    print(f"   Scopes: {credentials.scopes}")
    print(f"   Quota project: {getattr(credentials, 'quota_project_id', 'None')}")
    
    # Test raw HTTP request with token
    print(f"\n🌐 Raw HTTP Test:")
    headers = {'Authorization': f'Bearer {credentials.token}'}
    
    try:
        # Test Albums API directly
        url = 'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'
        response = requests.get(url, headers=headers)
        print(f"   Albums API Response: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"   Error body: {response.text}")
    except Exception as e:
        print(f"   Raw HTTP error: {e}")
    
    # Test different endpoints
    print(f"\n📱 Testing Different Endpoints:")
    
    try:
        service = build('photoslibrary', 'v1', credentials=credentials,
                       discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        
        # Try shared albums instead of regular albums
        print("   Testing shared albums...")
        try:
            results = service.sharedAlbums().list(pageSize=1).execute()
            print(f"   ✅ Shared albums work! Found: {len(results.get('sharedAlbums', []))}")
        except Exception as e:
            print(f"   ❌ Shared albums failed: {e}")
        
        # Try media items search without album
        print("   Testing media items search...")
        try:
            body = {"pageSize": 1}
            results = service.mediaItems().search(body=body).execute()
            print(f"   ✅ Media search works! Found: {len(results.get('mediaItems', []))}")
        except Exception as e:
            print(f"   ❌ Media search failed: {e}")
            
    except Exception as e:
        print(f"   Service creation failed: {e}")

if __name__ == '__main__':
    debug_token() 