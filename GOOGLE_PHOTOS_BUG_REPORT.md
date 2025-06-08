# Google Photos Library API Bug Report

## Issue Summary
Google Photos Library API returns `403 "Request had insufficient authentication scopes"` error despite OAuth token containing the correct `https://www.googleapis.com/auth/photoslibrary.readonly` scope.

## Environment Details
- **Date Reported**: 2025-06-07
- **OAuth Client Type**: Web Application
- **API**: Google Photos Library API v1
- **Client Library**: google-api-python-client (tested versions 2.70.0 and 2.83.0)
- **Platform**: Linux (Raspberry Pi OS)
- **Python Version**: 3.11

## Expected Behavior
OAuth token with `photoslibrary.readonly` scope should be able to access Google Photos Library API endpoints.

## Actual Behavior
All Google Photos Library API endpoints return:
```json
{
  "error": {
    "code": 403,
    "message": "Request had insufficient authentication scopes.",
    "status": "PERMISSION_DENIED"
  }
}
```

## Evidence

### 1. OAuth Token Contains Correct Scopes
Token verification via `https://oauth2.googleapis.com/tokeninfo` shows:
```json
{
  "scope": "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/photoslibrary.readonly",
  "aud": "454636387413-4r9e2oko48aq068qeqsereemdr3h064r.apps.googleusercontent.com",
  "exp": "1749371297",
  "access_type": "offline"
}
```

### 2. Same Token Works with Other Google APIs
The identical OAuth token successfully accesses Google Calendar API:
- ✅ `https://www.googleapis.com/calendar/v3/users/me/calendarList` - SUCCESS
- ❌ `https://photoslibrary.googleapis.com/v1/albums` - 403 insufficient scopes

### 3. Failed Endpoints (All return 403)
- `https://photoslibrary.googleapis.com/v1/albums`
- `https://photoslibrary.googleapis.com/v1/sharedAlbums`
- `https://photoslibrary.googleapis.com/v1/mediaItems:search`

### 4. OAuth Configuration
- Client Type: Web Application
- Redirect URI: `http://localhost:8080/authorize`
- Requested Scopes: 
  - `https://www.googleapis.com/auth/calendar.readonly`
  - `https://www.googleapis.com/auth/photoslibrary.readonly`
- OAuth Flow: authorization_code with refresh_token

## Reproduction Steps

1. Create OAuth 2.0 Web Application client in Google Cloud Console
2. Enable Google Photos Library API
3. Request authorization with scopes: `calendar.readonly` and `photoslibrary.readonly`
4. Complete OAuth flow and obtain access token
5. Verify token contains both scopes via tokeninfo endpoint
6. Test Calendar API - works ✅
7. Test Photos Library API - fails with 403 ❌

## Test Script
Run the attached `google_photos_api_bug_report.py` script to reproduce the issue:

```bash
python3 google_photos_api_bug_report.py
```

## Curl Commands for Manual Testing

```bash
# Verify token (works)
curl 'https://oauth2.googleapis.com/tokeninfo?access_token=TOKEN_HERE'

# Test Calendar API (works)
curl -H 'Authorization: Bearer TOKEN_HERE' \
     'https://www.googleapis.com/calendar/v3/users/me/calendarList'

# Test Photos API (fails with 403)
curl -H 'Authorization: Bearer TOKEN_HERE' \
     'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'
```

## Impact
- Prevents legitimate applications from accessing Google Photos Library API
- Affects multiple developers (see related Stack Overflow questions)
- Forces workarounds or disabling Photos integration

## Related Issues
- [Add any Stack Overflow links or similar issues you find]

## Additional Information
- Issue persists across different google-api-python-client versions
- Issue persists across different OAuth client configurations
- Raw HTTP requests and client library both fail identically
- Calendar API works perfectly with same token, proving OAuth setup is correct

---

**Request**: Please investigate why Google Photos Library API rejects properly scoped OAuth tokens that work with other Google APIs. 