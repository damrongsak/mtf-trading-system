#!/usr/bin/env python3
"""
Automatic Telegram Webhook Configuration
Reads webhook URL from .env and registers it with Telegram Bot API
"""
import os
import sys
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "mtf_olympus_webhook_secret")


def get_webhook_info():
    """Get current webhook configuration"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = httpx.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
        sys.exit(1)


def set_webhook():
    """Set webhook URL from .env configuration"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)
    
    if not TELEGRAM_WEBHOOK_URL:
        print("❌ TELEGRAM_WEBHOOK_URL not found in .env")
        print("Please add TELEGRAM_WEBHOOK_URL to your .env file")
        sys.exit(1)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {
        "url": TELEGRAM_WEBHOOK_URL,
        "secret_token": TELEGRAM_WEBHOOK_SECRET,
        "allowed_updates": ["message"]
    }
    
    print(f"📡 Setting webhook to: {TELEGRAM_WEBHOOK_URL}")
    
    try:
        response = httpx.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook configured successfully!")
            print(f"   URL: {TELEGRAM_WEBHOOK_URL}")
            print(f"   Secret: {TELEGRAM_WEBHOOK_SECRET}")
        else:
            print(f"❌ Failed to set webhook: {result.get('description')}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        sys.exit(1)


def delete_webhook():
    """Delete webhook configuration"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    
    try:
        response = httpx.post(url)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook deleted successfully!")
        else:
            print(f"❌ Failed to delete webhook: {result.get('description')}")
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python configure_webhook.py [setup|info|delete]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "setup":
        set_webhook()
    elif command == "info":
        info = get_webhook_info()
        print("\n📊 Current Webhook Configuration:")
        print(f"   URL: {info['result'].get('url', 'Not set')}")
        print(f"   Pending updates: {info['result'].get('pending_update_count', 0)}")
        print(f"   Max connections: {info['result'].get('max_connections', 0)}")
        if info['result'].get('last_error_message'):
            print(f"   ⚠️  Last error: {info['result']['last_error_message']}")
    elif command == "delete":
        delete_webhook()
    else:
        print(f"❌ Unknown command: {command}")
        print("Usage: python configure_webhook.py [setup|info|delete]")
        sys.exit(1)


if __name__ == "__main__":
    main()
