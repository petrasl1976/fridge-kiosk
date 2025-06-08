#!/usr/bin/env python3
"""
Alternative Google Photos API test with different approaches
"""

import json
import sys
from pathlib import Path
import requests

def test_with_requests_only():
    """Test using only requests library with different headers"""
    print("🧪 Testing with requests library only...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    token = token_data['token']
    
    # Try different header formats
    headers_variants = [
        {'Authorization': f'Bearer {token}'},
        {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        {'Authorization': f'Bearer {token}', 'X-Goog-AuthUser': '0'},
        {'Authorization': f'OAuth {token}'},  # Try OAuth instead of Bearer
    ]
    
    for i, headers in enumerate(headers_variants):
        print(f"   Variant {i+1}: {list(headers.keys())}")
        
        try:
            response = requests.get(
                'https://photoslibrary.googleapis.com/v1/albums?pageSize=1',
                headers=headers,
                timeout=10
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with variant {i+1}!")
                return True
            else:
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    return False

def test_token_info():
    """Check token info with Google's tokeninfo endpoint"""
    print("\n🔍 Checking token info...")
    
    token_path = Path(__file__).parent.parent.parent / 'config' / 'token.json'
    with open(token_path, 'r') as f:
        token_data = json.load(f)
    
    token = token_data['token']
    
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')
        if response.status_code == 200:
            info = response.json()
            print(f"   Token info: {json.dumps(info, indent=2)}")
            return info
        else:
            print(f"   Failed to get token info: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    return None

def main():
    print("🔬 Alternative Google Photos API Testing")
    print("=" * 50)
    
    # Test token info first
    token_info = test_token_info()
    
    # Test with pure requests
    success = test_with_requests_only()
    
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")

if __name__ == '__main__':
    main() 