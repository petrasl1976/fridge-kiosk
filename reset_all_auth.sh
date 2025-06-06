#!/bin/bash
echo "🔄 Completely resetting all authentication data..."

# Stop the backend service
sudo systemctl stop fridge-kiosk-backend.service

# Remove all auth-related files
rm -f fridge-kiosk/config/token.json
rm -f fridge-kiosk/config/.oauth_state
rm -f fridge-kiosk/plugins/google-photos/cache/error_state.json
rm -f fridge-kiosk/plugins/google-photos/cache/photos_cache.json

# Clear any remaining cache
rm -rf fridge-kiosk/plugins/google-photos/cache/*

echo "✅ All authentication data cleared"
echo "🚀 Starting backend service..."

# Start the backend service
sudo systemctl start fridge-kiosk-backend.service

echo "🌐 Now visit http://localhost:8080 and re-authenticate"
echo "⏰ After authentication, wait 5 minutes before testing" 