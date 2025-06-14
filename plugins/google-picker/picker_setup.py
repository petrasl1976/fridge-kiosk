#!/usr/bin/env python3
"""
Google Photos Picker Setup Utility for Fridge Kiosk

This utility helps you select photos from your Google Photos library using the Picker API.
This is a one-time setup process where you can select hundreds of photos at once.

After selection, your kiosk will display these photos automatically.

Usage:
    python picker_setup.py
"""

import os
import sys
import json
import logging
import time
import qrcode
from io import StringIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_credentials():
    """Get valid credentials from token.json."""
    token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'token.json')
    
    if not os.path.exists(token_path):
        logger.error(f"Token file not found at {token_path}")
        logger.error("Please run the authentication flow first")
        return None
    
    try:
        with open(token_path, 'r') as token_file:
            token_data = json.load(token_file)
            credentials = Credentials(**token_data)
            logger.info("Credentials loaded successfully")
            return credentials
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

def get_picker_service():
    """Get Google Photos Picker API service."""
    credentials = get_credentials()
    if not credentials:
        return None
    
    try:
        service = build(
            'photospicker', 'v1', 
            credentials=credentials,
            discoveryServiceUrl='https://photospicker.googleapis.com/$discovery/rest?version=v1'
        )
        logger.debug("Picker API service created successfully")
        return service
    except Exception as e:
        logger.error(f"Error creating Picker API service: {e}")
        return None

def create_picker_session():
    """Create a new picker session."""
    service = get_picker_service()
    if not service:
        return None
    
    try:
        # Create a new session
        response = service.sessions().create().execute()
        session_id = response['id']
        picker_uri = response['pickerUri']
        
        logger.info(f"✅ Picker session created successfully!")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   Picker URI: {picker_uri}")
        
        return {
            'session_id': session_id,
            'picker_uri': picker_uri,
            'polling_config': response.get('pollingConfig', {})
        }
    except HttpError as error:
        logger.error(f"❌ Error creating picker session: {error}")
        return None

def display_picker_info(session_info):
    """Display picker information and QR code to user."""
    picker_uri = session_info['picker_uri']
    
    print("\n" + "="*60)
    print("📸 GOOGLE PHOTOS PICKER SETUP")
    print("="*60)
    print()
    print("🔗 PICKER URL:")
    print(f"   {picker_uri}")
    print()
    print("📱 QR CODE:")
    print("   Scan this QR code with your phone to open the picker:")
    print()
    
    # Generate QR code
    try:
        qr = qrcode.QRCode(version=1, box_size=2, border=4)
        qr.add_data(picker_uri)
        qr.make(fit=True)
        
        # Print QR code to terminal
        qr.print_ascii(out=sys.stdout)
        print()
    except Exception as e:
        logger.warning(f"Could not generate QR code: {e}")
    
    print("📋 INSTRUCTIONS:")
    print("   1. Click the URL above or scan the QR code")
    print("   2. This will open Google Photos on your device")
    print("   3. Select as many photos/videos as you want for your kiosk")
    print("   4. Tap 'Done' when finished selecting")
    print("   5. Come back here and wait for the setup to complete")
    print()
    print("⏳ After you select photos, this script will automatically")
    print("   detect completion and save your selection.")
    print()
    print("="*60)

def poll_session(session_info):
    """Poll the session until media items are set."""
    service = get_picker_service()
    if not service:
        return False
    
    session_id = session_info['session_id']
    polling_config = session_info.get('polling_config', {})
    
    # Parse poll interval (might be "5s" or just "5")
    poll_interval_raw = polling_config.get('pollInterval', 5)
    if isinstance(poll_interval_raw, str) and poll_interval_raw.endswith('s'):
        poll_interval = int(poll_interval_raw[:-1])  # Remove 's' suffix
    else:
        poll_interval = int(poll_interval_raw)
    
    # Parse timeout (might be "1800s", "1799.895084s", or just "1800")
    timeout_raw = polling_config.get('timeoutIn', 1800)
    if isinstance(timeout_raw, str) and timeout_raw.endswith('s'):
        timeout_in = int(float(timeout_raw[:-1]))  # Remove 's' suffix and handle decimals
    else:
        timeout_in = int(float(timeout_raw))
    
    logger.info(f"⏳ Waiting for photo selection...")
    logger.info(f"   Poll interval: {poll_interval} seconds")
    logger.info(f"   Timeout: {timeout_in} seconds")
    print(f"\n🕐 Checking for selection every {poll_interval} seconds...")
    print("   (You can select photos on your device in the meantime)")
    
    start_time = time.time()
    
    while True:
        try:
            # Check if timeout reached
            elapsed = time.time() - start_time
            if elapsed > timeout_in:
                logger.error(f"❌ Session timed out after {timeout_in} seconds")
                return False
            
            # Poll the session
            response = service.sessions().get(sessionId=session_id).execute()
            media_items_set = response.get('mediaItemsSet', False)
            
            if media_items_set:
                logger.info("✅ Photo selection completed!")
                return True
            
            # Update polling config if provided
            new_polling_config = response.get('pollingConfig', {})
            if new_polling_config:
                poll_interval_raw = new_polling_config.get('pollInterval', poll_interval)
                if isinstance(poll_interval_raw, str) and poll_interval_raw.endswith('s'):
                    poll_interval = int(float(poll_interval_raw[:-1]))  # Remove 's' suffix and handle decimals
                else:
                    poll_interval = int(float(poll_interval_raw))
            
            # Wait before next poll
            print(f"   ⏳ Still waiting... ({elapsed:.0f}/{timeout_in}s)")
            time.sleep(poll_interval)
            
        except HttpError as error:
            logger.error(f"❌ Error polling session: {error}")
            return False
        except KeyboardInterrupt:
            logger.info("\n❌ Setup interrupted by user")
            return False

def retrieve_selected_photos(session_info):
    """Retrieve the selected photos from the session."""
    service = get_picker_service()
    if not service:
        return []
    
    session_id = session_info['session_id']
    
    try:
        # Get all selected media items
        photos = []
        page_token = None
        
        while True:
            if page_token:
                response = service.mediaItems().list(
                    sessionId=session_id,
                    pageToken=page_token
                ).execute()
            else:
                response = service.mediaItems().list(sessionId=session_id).execute()
            
            batch_photos = response.get('mediaItems', [])
            photos.extend(batch_photos)
            
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        
        logger.info(f"📸 Retrieved {len(photos)} selected photos")
        
        # Log photo details
        for i, photo in enumerate(photos[:5]):  # Show first 5
            filename = photo.get('filename', 'Unknown')
            mime_type = photo.get('mimeType', 'Unknown')
            logger.info(f"   {i+1}. {filename} ({mime_type})")
        
        if len(photos) > 5:
            logger.info(f"   ... and {len(photos) - 5} more photos")
        
        return photos
        
    except HttpError as error:
        logger.error(f"❌ Error retrieving selected photos: {error}")
        return []

def save_selected_photos(photos):
    """Save selected photos to cache."""
    # Import from main plugin
    import sys
    sys.path.append(os.path.dirname(__file__))
    from main import save_selected_photos as save_photos, ensure_cache_dir
    
    ensure_cache_dir()
    save_photos(photos)
    logger.info(f"💾 Saved {len(photos)} photos to cache")

def cleanup_session(session_info):
    """Clean up the picker session."""
    service = get_picker_service()
    if not service:
        return
    
    session_id = session_info['session_id']
    
    try:
        service.sessions().delete(sessionId=session_id).execute()
        logger.info("🧹 Session cleaned up successfully")
    except HttpError as error:
        logger.warning(f"Warning: Could not clean up session: {error}")

def main():
    """Main function to run the picker setup."""
    print("🚀 Starting Google Photos Picker Setup...")
    print()
    
    # Step 1: Create picker session
    print("1️⃣  Creating picker session...")
    session_info = create_picker_session()
    if not session_info:
        print("❌ Failed to create picker session. Check your credentials and try again.")
        sys.exit(1)
    
    try:
        # Step 2: Display picker info to user
        display_picker_info(session_info)
        
        # Step 3: Wait for user to select photos
        print("2️⃣  Waiting for photo selection...")
        if not poll_session(session_info):
            print("❌ Photo selection was not completed.")
            return
        
        # Step 4: Retrieve selected photos
        print("\n3️⃣  Retrieving selected photos...")
        photos = retrieve_selected_photos(session_info)
        if not photos:
            print("❌ No photos were selected or could not retrieve photos.")
            return
        
        # Step 5: Save photos to cache
        print("4️⃣  Saving photos to cache...")
        save_selected_photos(photos)
        
        # Success!
        print()
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"✅ Selected and cached: {len(photos)} photos/videos")
        print("✅ Your kiosk will now display these photos automatically")
        print("✅ Photos are cached and will be available offline")
        print()
        print("🔄 To select different photos in the future:")
        print("   Run this setup script again")
        print()
        print("🚀 You can now start/restart your kiosk!")
        
    finally:
        # Step 6: Clean up session
        print("\n5️⃣  Cleaning up session...")
        cleanup_session(session_info)

if __name__ == "__main__":
    main() 