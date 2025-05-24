# Google Calendar Plugin

This plugin displays upcoming events from your Google Calendar on the Fridge Kiosk display.

## Features

- Displays upcoming calendar events
- Shows event time, title, and location
- Configurable number of events to display
- Configurable lookahead period
- OAuth2 authentication with Google

## Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials (Web application type)
4. Download the credentials as `client_secret.json`
5. Place `client_secret.json` in the `config` directory
6. Run the authentication server:
   ```bash
   python auth_server.py
   ```
7. Follow the authentication flow in your browser
8. Restart the Fridge Kiosk application

## Configuration

The following environment variables can be set in your `.env` file:

- `GOOGLE_CALENDAR_ID`: The ID of the calendar to display (default: 'primary')
- `GOOGLE_CALENDAR_MAX_EVENTS`: Maximum number of events to display (default: 10)
- `GOOGLE_CALENDAR_LOOKAHEAD_DAYS`: Number of days to look ahead for events (default: 7)

## Dependencies

- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client

## License

This plugin is licensed under the MIT License. 