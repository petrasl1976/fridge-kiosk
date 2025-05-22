# Google Authentication Server

This is a centralized authentication server for Google APIs in the Fridge Kiosk system. It handles OAuth2 authentication for various Google services like Google Calendar, Google Photos, etc.

## Features

- Single shared authentication flow for multiple Google services
- Automatic token refresh
- Custom scopes based on the requested service
- Web interface for authentication status and management

## Usage

To start the authentication server for a specific Google service:

```bash
python3 -m backend.utils.auth.google_auth_server --service "Google Calendar"
```

By default, the server will try to run on port 8090. If that port is in use, it will try ports 8095, 8100, 8105, and 8110.

Available services:
- `Google Calendar` - Uses calendar.readonly scope
- `Google Photos` - Uses photoslibrary.readonly scope
- Custom services with specific scopes can be added by modifying the code

## Requirements

- flask
- google-auth
- google-auth-oauthlib
- google-api-python-client
- requests

## Adding a new Google service

1. Add a new section in the `authorize()` function to specify the appropriate scopes for your service
2. Update any plugin code to reference the centralized auth server

Example:
```python
# In authorize() function
if service == 'calendar':
    scopes = ['https://www.googleapis.com/auth/calendar.readonly']
elif service == 'photos':
    scopes = ['https://www.googleapis.com/auth/photoslibrary.readonly']
elif service == 'your-new-service':
    scopes = ['https://www.googleapis.com/auth/your-service-scope']
else:
    scopes = DEFAULT_SCOPES
``` 