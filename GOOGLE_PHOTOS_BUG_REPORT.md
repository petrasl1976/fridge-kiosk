# Google Photos Library API Bug Report

## Issue Summary
Google Photos Library API returns `403 "Request had insufficient authentication scopes"` error despite OAuth token containing the correct `https://www.googleapis.com/auth/photoslibrary.readonly` scope. **Additionally, Google's own APIs give contradictory responses for the same token.**

## Environment Details
- **Date Reported**: 2025-01-03
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

**More concerning: Google's own APIs give contradictory responses for the same token.**

## Evidence

### 1. OAuth Token Contains Correct Scopes
Token stored in application contains both required scopes:
```json
{
  "scopes": [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly"
  ]
}
```

### 2. Google's APIs Give Contradictory Responses for Same Token
**The same OAuth token produces different results across Google services:**

- ❌ **Google tokeninfo endpoint**: `400 "invalid_token"` 
- ✅ **Google Calendar API**: Successfully returns calendar data
- ❌ **Google Photos API**: `403 "insufficient authentication scopes"`

**This is impossible if the token was truly invalid - Calendar API would also fail.**

### 3. Successful API Calls (Proving Token Validity)
The identical OAuth token successfully accesses:
- ✅ `https://www.googleapis.com/calendar/v3/users/me/calendarList` - Returns 2 calendars
- ✅ All other Calendar API endpoints work perfectly

### 4. Failed API Calls (Same Token)
The same token fails on all Photos API endpoints:
- ❌ `https://photoslibrary.googleapis.com/v1/albums` - 403 insufficient scopes
- ❌ `https://photoslibrary.googleapis.com/v1/sharedAlbums` - 403 insufficient scopes
- ❌ `https://photoslibrary.googleapis.com/v1/mediaItems:search` - 403 insufficient scopes

### 5. OAuth Configuration
- Client Type: Web Application
- Redirect URI: `http://localhost:8080/authorize`
- Requested Scopes: 
  - `https://www.googleapis.com/auth/calendar.readonly`
  - `https://www.googleapis.com/auth/photoslibrary.readonly`
- OAuth Flow: authorization_code with refresh_token

## Reproduction Steps

1. Create OAuth 2.0 Web Application client in Google Cloud Console
2. Enable both Google Calendar API and Google Photos Library API
3. Request authorization with scopes: `calendar.readonly` and `photoslibrary.readonly`
4. Complete OAuth flow and obtain access token
5. Test Calendar API - works ✅
6. Test Google tokeninfo endpoint - fails ❌ ("invalid token")
7. Test Photos Library API - fails ❌ (403 insufficient scopes)

**Result: Same token gives contradictory responses across Google services.**

## Test Script
Run the attached `google_photos_api_bug_report_v2.py` script to reproduce the issue:

```bash
python3 google_photos_api_bug_report_v2.py
```

**Expected output showing the contradiction:**
```
📅 Google Calendar API: SUCCESS ✅ (finds calendars)
🔍 Google tokeninfo: FAILED ❌ (says "invalid token") 
📸 Google Photos API: FAILED ❌ (says "insufficient scopes")
→ This is impossible if token was truly invalid!
```

## Curl Commands for Manual Testing

```bash
# Test Calendar API (works - proves token is valid)
curl -H 'Authorization: Bearer YOUR_TOKEN' \
     'https://www.googleapis.com/calendar/v3/users/me/calendarList'

# Test Photos API (fails with same token - THE BUG)
curl -H 'Authorization: Bearer YOUR_TOKEN' \
     'https://photoslibrary.googleapis.com/v1/albums?pageSize=1'

# Test Google's tokeninfo (inconsistent - also fails)
curl 'https://oauth2.googleapis.com/tokeninfo?access_token=YOUR_TOKEN'
```

## Impact
- Prevents legitimate applications from accessing Google Photos Library API
- Google's own services give contradictory responses for the same token
- Forces developers to assume their OAuth implementation is wrong when it's actually correct
- Affects multiple developers (similar issues reported on Stack Overflow)

## Root Cause Analysis
This appears to be an inconsistency between Google's authentication services:
1. **OAuth authorization flow** correctly grants the `photoslibrary.readonly` scope
2. **Calendar API authentication** correctly validates the token  
3. **Photos API authentication** incorrectly rejects the same token
4. **Tokeninfo endpoint** also gives inconsistent results

## Request for Google Engineering Team
Please investigate why:
1. Google Photos Library API rejects tokens that work with other Google APIs
2. Google's tokeninfo endpoint reports tokens as "invalid" when they work with Calendar API
3. The same OAuth token produces contradictory authentication results across Google services

---

**Attached Files:**
- `google_photos_api_bug_report_v2.py` - Reproduction script
- Evidence logs showing contradictory API responses 