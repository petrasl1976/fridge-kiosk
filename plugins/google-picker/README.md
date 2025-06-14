# Google Photos Picker Plugin

This plugin displays photos and videos selected from your Google Photos library using the Google Photos Picker API.

## ✨ Features

- **One-time setup**: Select hundreds of photos at once
- **Automatic display**: Kiosk displays selected photos without manual intervention  
- **Cached photos**: Works offline after initial setup
- **Secure selection**: Uses Google's official Picker API
- **Full control**: You choose exactly which photos to display

## 🔧 Setup

### 1. Configure Google Cloud Console

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Photos Picker API** (not the Library API)
3. Create OAuth 2.0 credentials (Web application type)
4. **Required scope**: `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`
5. Download credentials as `client_secret.json`
6. Place `client_secret.json` in the `config` directory

### 2. Run Authentication

```bash
# Run the main authentication server
python auth_server.py
```

Follow the authentication flow in your browser.

### 3. Select Photos (One-Time Setup)

```bash
# Run the picker setup utility
python plugins/google-picker/picker_setup.py
```

This will:
1. Create a picker session
2. Display a URL and QR code
3. Open Google Photos on your device
4. Let you select photos/videos
5. Cache your selection locally

### 4. Start Your Kiosk

Your kiosk will now automatically display the selected photos!

## 📋 How It Works

### One-Time Setup Process:
1. **Run Setup**: `python plugins/google-picker/picker_setup.py`
2. **Select Photos**: Use the provided URL or QR code to select photos in Google Photos
3. **Automatic Caching**: Selected photos are cached locally
4. **Kiosk Display**: Your kiosk displays the cached photos automatically

### Daily Operation:
- No manual intervention needed
- Kiosk cycles through your selected photos
- Works offline (uses cached photo URLs)
- Photos refresh automatically

## ⚙️ Configuration

Edit `config.json` to customize settings:

```json
{
    "settings": {
        "photo_duration": 30,        // Seconds to display each photo
        "video_duration": 60,        // Seconds to display each video  
        "media_types": "all",        // "all", "photo", or "video"
        "video_sound": false,        // Enable video sound
        "sequence_count": 6,         // Photos per batch
        "label_font_size": "2.5em",  // Font size for labels
        "auto_refresh_hours": 24     // Hours between cache refresh
    }
}
```

## 🔄 Updating Your Selection

To select different photos:

```bash
# Run setup again to select new photos
python plugins/google-picker/picker_setup.py
```

This will replace your current selection with newly selected photos.

## 🆚 Picker API vs Library API

| Feature | Picker API (This Plugin) | Library API (google-photos plugin) |
|---------|-------------------------|----------------------------------|
| **Status** | ✅ Active | ❌ Deprecated (March 2025) |
| **Access** | Your entire Google Photos library | Only app-created content |
| **Setup** | One-time photo selection | Required photo upload |
| **User Control** | You choose specific photos | Automatic random selection |
| **Offline** | ✅ Works with cached URLs | ❌ Requires API access |

## 🚨 Important Notes

- **One-time setup required**: You must run the picker setup before the kiosk can display photos
- **Photo selection**: You can select as many photos as you want in a single session
- **Cache expiry**: Selected photos are cached for 7 days, then require re-selection
- **Internet required**: For initial setup and photo URL access (not for kiosk operation)

## 🛠️ Troubleshooting

### "No photos available. Run picker setup first."
- Run: `python plugins/google-picker/picker_setup.py`

### "Failed to create picker session"
- Check your credentials in `config/token.json`
- Verify Google Photos Picker API is enabled
- Ensure correct OAuth scopes

### "Session timed out"
- Setup sessions expire after 30 minutes
- Run the setup script again if needed

### Photos not loading
- Check internet connection for photo URL access
- Run setup again to refresh photo cache

## 📦 Dependencies

- google-api-python-client>=2.0.0
- google-auth-httplib2>=0.1.0
- google-auth-oauthlib>=0.4.0
- requests>=2.31.0
- qrcode>=7.0 (for setup utility)

## 📄 License

This plugin is licensed under the MIT License. 