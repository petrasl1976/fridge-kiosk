# Google Calendar Plugin

This plugin displays events from a Google Calendar on your Fridge Kiosk.

## Setup Instructions

### 1. Create Google API Project and Enable Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API for your project
4. Create OAuth 2.0 credentials (Web application type)
5. Add `http://localhost:8090/oauth2callback` to Authorized redirect URIs
6. Download the credentials JSON file as `client_secret.json`
7. Place this file in the `fridge-kiosk/config` directory

### 2. Configure Environment Variables

Create or edit the `.env` file in the `fridge-kiosk/config` directory with:

```
# By default, this uses your primary calendar
# To use a specific calendar, find the calendar ID in Google Calendar settings
GOOGLE_CALENDAR_ID=primary
```

### 3. Run Authentication

Run the authentication server to authorize the application with Google:

```bash
cd fridge-kiosk
python3 -m backend.utils.auth.google_auth_server --service "Google Calendar"
```

This will open a browser window. Log in with your Google account and authorize the app.

### 4. Restart the Kiosk Backend

Restart the kiosk backend service to apply the changes:

```bash
sudo systemctl restart fridge-kiosk-backend.service
```

## Troubleshooting

If the calendar is not displaying correctly, run the repair tool:

```bash
cd fridge-kiosk
python3 plugins/google-calendar/repair.py
```

This will check for common issues and guide you through fixing them.

## Features

- Displays a monthly calendar view with events
- Color-codes events based on their prefixes
- Shows today's events with time information
- Automatically refreshes data based on the configured interval

## Configuration

You can adjust the plugin's settings in the `config.json` file:

- `updateInterval`: How often to refresh data (in seconds)
- `options.weeks_to_show`: Number of weeks to display (default: 4)
- `options.event_summary_max_length`: Maximum length for event titles before truncating
- `options.show_holidays`: Whether to show holidays in the calendar view 