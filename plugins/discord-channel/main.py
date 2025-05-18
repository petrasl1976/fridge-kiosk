import os
import requests
import logging
from dotenv import load_dotenv
from pathlib import Path

# Get the project root directory (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / 'config' / '.env'

# Load environment variables from the specific .env file
load_dotenv(ENV_FILE)

# Configure logging
logger = logging.getLogger('fridge-kiosk')

# Debug logging for .env file
logger.info(f"Looking for .env file at: {ENV_FILE}")
logger.info(f".env file exists: {ENV_FILE.exists()}")

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_TEXT_CHANNEL_ID")
API_BASE_URL = "https://discord.com/api/v9"
MESSAGE_COUNT = int(os.getenv("DISCORD_MESSAGE_COUNT", 10))

# Debug logging for environment variables
logger.info(f"Discord BOT_TOKEN length: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
logger.info(f"Discord CHANNEL_ID: {CHANNEL_ID}")

# Spalvos paimamos iš pagrindinio config per JS, čia backend nieko nehardcodina

def get_username_color(username):
    """Generate a consistent color for a username"""
    import hashlib
    hash_object = hashlib.md5(username.encode())
    hex_dig = hash_object.hexdigest()
    return f"#{hex_dig[:6]}"

def api_data():
    """
    API handler for /api/plugins/discord-channel/data
    """
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.error(f"Discord configuration missing - BOT_TOKEN: {'present' if BOT_TOKEN else 'missing'}, CHANNEL_ID: {'present' if CHANNEL_ID else 'missing'}")
        return {"error": "Discord BOT_TOKEN or CHANNEL_ID not set"}

    url = f"{API_BASE_URL}/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    params = {"limit": MESSAGE_COUNT}

    try:
        logger.info(f"Fetching Discord messages from channel {CHANNEL_ID}")
        r = requests.get(url, headers=headers, params=params, timeout=5)
        
        if r.status_code == 200:
            messages = r.json()
            
            # Process each message
            for m in messages:
                username = m['author']['username']
                m['color'] = get_username_color(username)
                
                # Ensure images are not suppressed (Proxy URLs are not filtered)
                if 'attachments' in m and m['attachments']:
                    for attachment in m['attachments']:
                        if 'proxy_url' in attachment and not 'url' in attachment:
                            attachment['url'] = attachment['proxy_url']
                
                # Ensure embed images are not suppressed
                if 'embeds' in m and m['embeds']:
                    for embed in m['embeds']:
                        if 'image' in embed and 'proxy_url' in embed['image'] and not 'url' in embed['image']:
                            embed['image']['url'] = embed['image']['proxy_url']
                        if 'thumbnail' in embed and 'proxy_url' in embed['thumbnail'] and not 'url' in embed['thumbnail']:
                            embed['thumbnail']['url'] = embed['thumbnail']['proxy_url']
            
            logger.info(f"Successfully fetched {len(messages)} Discord messages")
            return messages
            
        logger.error(f"Failed to fetch Discord messages: {r.status_code}")
        return {"error": f"Unable to fetch messages: {r.status_code}"}
        
    except Exception as e:
        logger.error(f"Error fetching Discord messages: {str(e)}")
        return {"error": str(e)}

def init(config):
    """
    Initialize the plugin (not used, but required by plugin loader)
    """
    return {"data": {}} 