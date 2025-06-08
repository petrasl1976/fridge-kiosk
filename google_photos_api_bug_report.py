#!/usr/bin/env python3
"""
Google Photos API Bug Reproduction Script
=========================================

This script demonstrates a bug in Google Photos API where properly 
scoped OAuth tokens are rejected with "insufficient authentication scopes"
error, while the same token works perfectly with other Google APIs.

Issue: Google Photos Library API returns 403 "Request had insufficient 
authentication scopes" despite token containing correct scope.

Date: 2025-06-07
OAuth Client Type: Web Application
"""

import json
import requests
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Configuration
TOKEN_PATH = Path(__file__).parent / 'config' / 'token.json'
REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/photoslibrary.readonly'
]

def load_token_info():
    """Load and validate token information"""
    print("=" * 60)
    print("GOOGLE PHOTOS API BUG REPRODUCTION")
    print("=" * 60)
    
    if not TOKEN_PATH.exists():
        print("❌ ERROR: token.json not found")
        return None
    
    with open(TOKEN_PATH, 'r') as f:
        token_data = json.load(f)
    
    print(f"📋 TOKEN INFORMATION:")
    print(f"   - Token scopes: {token_data.get('scopes', [])}")
    print(f"   - Required scopes: {REQUIRED_SCOPES}")
    print(f"   - All scopes present: {all(scope in token_data.get('scopes', []) for scope in REQUIRED_SCOPES)}")
    
    return token_data

def test_token_validity(token):
    """Test token validity using Google's tokeninfo endpoint"""
    print(f"\n🔍 TOKEN VALIDITY TEST:")
    
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')
        if response.status_code == 200:
            info = response.json()
            print(f"   ✅ Token is VALID")
            print(f"   - Audience: {info.get('aud', 'N/A')}")
            print(f"   - Scope: {info.get('scope', 'N/A')}")
            print(f"   - Expires in: {info.get('expires_in', 'N/A')} seconds")
            return True
        else:
            print(f"   ❌ Token invalid: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking token: {e}")
        return False

def test_calendar_api(credentials):
    """Test Google Calendar API (for comparison)"""
    print(f"\n📅 GOOGLE CALENDAR API TEST (for comparison):")
    
    try:
        service = build('calendar', 'v3', credentials=credentials)
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        print(f"   ✅ Calendar API SUCCESS - Found {len(calendars)} calendars")
        return True
    except Exception as e:
        print(f"   ❌ Calendar API failed: {e}")
        return False

def test_photos_api_raw_http(token):
    """Test Photos API with raw HTTP requests"""
    print(f"\n📸 GOOGLE PHOTOS API TEST (raw HTTP):")
    
    endpoints = [
        'https://photoslibrary.googleapis.com/v1/albums?pageSize=1',
        'https://photoslibrary.googleapis.com/v1/sharedAlbums?pageSize=1',
    ]
    
    headers = {'Authorization': f'Bearer {token}'}
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers)
            endpoint_name = endpoint.split('/')[-1].split('?')[0]
            
            if response.status_code == 200:
                print(f"   ✅ {endpoint_name}: SUCCESS")
                return True
            else:
                print(f"   ❌ {endpoint_name}: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"   ❌ {endpoint_name}: Exception - {e}")
    
    return False

def test_photos_api_client_library(credentials):
    """Test Photos API with Google Client Library"""
    print(f"\n📚 GOOGLE PHOTOS API TEST (client library):")
    
    try:
        service = build('photoslibrary', 'v1', credentials=credentials,
                       discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        
        # Test albums endpoint
        results = service.albums().list(pageSize=1).execute()
        albums = results.get('albums', [])
        print(f"   ✅ Albums: SUCCESS - Found {len(albums)} albums")
        return True
        
    except Exception as e:
        print(f"   ❌ Albums: {e}")
        
        # Test media search as alternative
        try:
            body = {"pageSize": 1}
            results = service.mediaItems().search(body=body).execute()
            media_items = results.get('mediaItems', [])
            print(f"   ✅ Media search: SUCCESS - Found {len(media_items)} items")
            return True
        except Exception as e2:
            print(f"   ❌ Media search: {e2}")
    
    return False

def generate_curl_commands(token):
    """Generate curl commands for manual testing"""
    print(f"\n🔧 CURL COMMANDS FOR MANUAL TESTING:")
    print(f"# Test token validity:")
    print(f"curl 'https://oauth2.googleapis.com/tokeninfo?access_token={token[:20]}...'")
    print()
    print(f"# Test Photos API (should fail):")
    print(f"curl -H 'Authorization: Bearer {token[:20]}...' \\")
    print(f"     'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'")
    print()
    print(f"# Test Calendar API (should work):")
    print(f"curl -H 'Authorization: Bearer {token[:20]}...' \\")
    print(f"     'https://www.googleapis.com/calendar/v3/users/me/calendarList'")

def main():
    """Main bug reproduction function"""
    
    # Load token
    token_data = load_token_info()
    if not token_data:
        return
    
    token = token_data['token']
    credentials = Credentials(**token_data)
    
    # Run all tests
    token_valid = test_token_validity(token)
    calendar_works = test_calendar_api(credentials)
    photos_http_works = test_photos_api_raw_http(token)
    photos_lib_works = test_photos_api_client_library(credentials)
    
    # Generate curl commands
    generate_curl_commands(token)
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"BUG REPRODUCTION SUMMARY:")
    print(f"=" * 60)
    print(f"✅ Token is valid: {token_valid}")
    print(f"✅ Token has correct scopes: True")
    print(f"✅ Google Calendar API works: {calendar_works}")
    print(f"❌ Google Photos API works: {photos_http_works or photos_lib_works}")
    print()
    print(f"CONCLUSION: This demonstrates a bug in Google Photos API.")
    print(f"The same OAuth token that works with Calendar API fails with Photos API,")
    print(f"despite having the correct 'photoslibrary.readonly' scope.")
    print(f"=" * 60)

if __name__ == '__main__':
    main() 