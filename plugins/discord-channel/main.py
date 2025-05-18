import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
API_BASE_URL = "https://discord.com/api/v9"
MESSAGE_COUNT = int(os.getenv("DISCORD_MESSAGE_COUNT", 10))

# Spalvos paimamos iš pagrindinio config per JS, čia backend nieko nehardcodina

def api_data():
    """
    API handler for /api/plugins/discord-channel/data
    """
    if not BOT_TOKEN or not CHANNEL_ID:
        return {"error": "Discord BOT_TOKEN or CHANNEL_ID not set"}
    url = f"{API_BASE_URL}/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    params = {"limit": MESSAGE_COUNT}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        if r.status_code == 200:
            messages = r.json()
            return messages
        return {"error": f"Unable to fetch messages: {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def init(config):
    """
    Initialize the plugin (not used, but required by plugin loader)
    """
    return {"data": {}} 