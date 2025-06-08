#!/usr/bin/env python3
"""
Refresh Google OAuth token
"""

import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def refresh_token():
    print("🔄 Refreshing Google OAuth token...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    
    if not token_path.exists():
        print("❌ token.json not found!")
        return False
    
    # Load current token
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    print(f"📋 Current token info:")
    print(f"   - Has refresh_token: {bool(token_data.get('refresh_token'))}")
    print(f"   - Token: {token_data.get('token', '')[:20]}...")
    
    try:
        # Create credentials
        credentials = Credentials(**token_data)
        print(f"   - Expired: {credentials.expired}")
        print(f"   - Valid: {credentials.valid}")
        
        # Force refresh
        print("\n🔄 Attempting to refresh...")
        request = Request()
        credentials.refresh(request)
        
        print("✅ Token refreshed successfully!")
        
        # Save refreshed token
        refreshed_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
        }
        
        with open(token_path, 'w') as f:
            json.dump(refreshed_data, f, indent=2)
        
        print(f"💾 Saved refreshed token")
        print(f"   - New token: {credentials.token[:20]}...")
        print(f"   - Scopes: {credentials.scopes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Refresh failed: {e}")
        return False

if __name__ == '__main__':
    success = refresh_token()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}") 