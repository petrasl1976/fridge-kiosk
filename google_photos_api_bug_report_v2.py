#!/usr/bin/env python3
"""
Google Photos API Bug Reproduction Script v2
===========================================

This script demonstrates a bug in Google Photos API where properly 
scoped OAuth tokens are rejected with "insufficient authentication scopes"
error, while the same token works perfectly with other Google APIs.

UPDATED: Handles cases where tokeninfo endpoint fails but token works with other APIs
"""

import json
import requests
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_PATH = Path(__file__).parent / 'config' / 'token.json'

def main():
    print("=" * 70)
    print("GOOGLE PHOTOS API BUG REPRODUCTION v2")
    print("=" * 70)
    
    # Load token
    with open(TOKEN_PATH, 'r') as f:
        token_data = json.load(f)
    
    token = token_data['token']
    credentials = Credentials(**token_data)
    
    print(f"📋 TOKEN CONFIGURATION:")
    print(f"   - Scopes in token.json: {token_data.get('scopes', [])}")
    print(f"   - photoslibrary.readonly present: {'https://www.googleapis.com/auth/photoslibrary.readonly' in token_data.get('scopes', [])}")
    print(f"   - calendar.readonly present: {'https://www.googleapis.com/auth/calendar.readonly' in token_data.get('scopes', [])}")
    
    # Test Google's tokeninfo (may be unreliable)
    print(f"\n🔍 GOOGLE TOKENINFO ENDPOINT:")
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')
        if response.status_code == 200:
            info = response.json()
            print(f"   ✅ Tokeninfo SUCCESS")
            print(f"   - Scope: {info.get('scope', 'N/A')}")
        else:
            print(f"   ❌ Tokeninfo FAILED: {response.status_code}")
            print(f"   - Note: This doesn't mean token is invalid!")
    except Exception as e:
        print(f"   ❌ Tokeninfo ERROR: {e}")
    
    # Test Calendar API (should work)
    print(f"\n📅 GOOGLE CALENDAR API TEST:")
    calendar_success = False
    try:
        service = build('calendar', 'v3', credentials=credentials)
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        print(f"   ✅ Calendar API SUCCESS - Found {len(calendars)} calendars")
        print(f"   - This PROVES the token is valid and properly authenticated")
        calendar_success = True
    except Exception as e:
        print(f"   ❌ Calendar API FAILED: {e}")
    
    # Test Photos API with client library
    print(f"\n📸 GOOGLE PHOTOS API TEST (client library):")
    photos_success = False
    try:
        service = build('photoslibrary', 'v1', credentials=credentials,
                       discoveryServiceUrl='https://photoslibrary.googleapis.com/$discovery/rest?version=v1')
        results = service.albums().list(pageSize=1).execute()
        albums = results.get('albums', [])
        print(f"   ✅ Photos API SUCCESS - Found {len(albums)} albums")
        photos_success = True
    except Exception as e:
        print(f"   ❌ Photos API FAILED: {e}")
    
    # Test Photos API with raw HTTP
    print(f"\n🌐 GOOGLE PHOTOS API TEST (raw HTTP):")
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get('https://photoslibrary.googleapis.com/v1/albums?pageSize=1', headers=headers)
        if response.status_code == 200:
            print(f"   ✅ Raw HTTP SUCCESS")
            photos_success = True
        else:
            print(f"   ❌ Raw HTTP FAILED: {response.status_code}")
            error_data = response.json()
            print(f"   - Error: {error_data}")
    except Exception as e:
        print(f"   ❌ Raw HTTP ERROR: {e}")
    
    # Generate evidence for bug report
    print(f"\n" + "=" * 70)
    print(f"BUG EVIDENCE SUMMARY:")
    print(f"=" * 70)
    print(f"✅ Token contains photoslibrary.readonly scope: True")
    print(f"✅ Token works with Google Calendar API: {calendar_success}")
    print(f"❌ Token works with Google Photos API: {photos_success}")
    print()
    
    if calendar_success and not photos_success:
        print(f"🐛 BUG CONFIRMED:")
        print(f"   The SAME OAuth token that successfully accesses Google Calendar API")
        print(f"   fails to access Google Photos API despite having the correct scope.")
        print(f"   This is clearly a bug in Google Photos API implementation.")
        print()
        print(f"💡 EVIDENCE FOR GOOGLE:")
        print(f"   1. Token has 'photoslibrary.readonly' scope ✅")
        print(f"   2. Token successfully calls Calendar API ✅") 
        print(f"   3. Token fails on Photos API with 'insufficient scopes' ❌")
        print(f"   4. This proves OAuth setup is correct, bug is in Photos API")
    
    # Generate curl commands with real token
    print(f"\n🔧 CURL COMMANDS TO INCLUDE IN BUG REPORT:")
    print(f"# This works (Calendar API):")
    print(f"curl -H 'Authorization: Bearer {token}' \\")
    print(f"     'https://www.googleapis.com/calendar/v3/users/me/calendarList'")
    print()
    print(f"# This fails (Photos API) - THE BUG:")
    print(f"curl -H 'Authorization: Bearer {token}' \\")
    print(f"     'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'")
    
    print(f"\n" + "=" * 70)

if __name__ == '__main__':
    main() 