# Google Photos Plugin

This plugin displays photos and videos from your Google Photos albums on the Fridge Kiosk display.

## Features

- Displays photos and videos from random albums
- Automatic slideshow with configurable duration
- Support for both photos and videos
- Album title display
- Progress bar for media duration
- Caching of album list for better performance

## Setup

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Photos Library API
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

The following settings can be configured in `config.json`:

- `photo_duration`: Duration in seconds to display each photo (default: 30)
- `video_duration`: Maximum duration in seconds to display each video (default: 60)
- `media_types`: Types of media to display ("photo", "video", or "all")
- `video_sound`: Whether to play video sound (default: false)
- `batch_size`: Number of media items to fetch at once (default: 5)
- `cache_expiration`: Album list cache expiration in seconds (default: 30 days)

## Dependencies

- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- requests

## License

This plugin is licensed under the MIT License. 