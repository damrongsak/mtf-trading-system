#!/usr/bin/env python3
"""
Setup Telegram Webhook
Registers the webhook URL with Telegram Bot API.
"""
import asyncio
import httpx
import os
import sys

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")  # e.g., https://yourdomain.com/api/v1/telegram/webhook
SECRET_TOKEN = os.getenv("TELEGRAM_WEBHOOK_SECRET", "mtf_olympus_webhook_secret")


async def setup_webhook():
    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    if not WEBHOOK_URL:
        print("❌ Error: TELEGRAM_WEBHOOK_URL environment variable not set")
        print("Example: export TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/v1/telegram/webhook")
        sys.exit(1)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {
        "url": WEBHOOK_URL,
        "secret_token": SECRET_TOKEN,
        "allowed_updates": ["message"]
    }
    
    print(f"🔧 Setting up Telegram webhook...")
    print(f"   Webhook URL: {WEBHOOK_URL}")
    print(f"   Secret Token: {SECRET_TOKEN[:10]}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook registered successfully!")
            print(f"   Response: {result}")
        else:
            print(f"❌ Failed to register webhook: {result}")
            sys.exit(1)


async def get_webhook_info():
    """Get current webhook configuration"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        result = response.json()
        
        if result.get("ok"):
            info = result.get("result", {})
            print("\n📊 Current Webhook Info:")
            print(f"   URL: {info.get('url', 'Not set')}")
            print(f"   Pending Updates: {info.get('pending_update_count', 0)}")
            if info.get("last_error_message"):
                print(f"   Last Error: {info.get('last_error_message')}")
        else:
            print(f"❌ Failed to get webhook info: {result}")


async def delete_webhook():
    """Delete the current webhook"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url)
        result = response.json()
        
        if result.get("ok"):
            print("✅ Webhook deleted successfully!")
        else:
            print(f"❌ Failed to delete webhook: {result}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Telegram webhook")
    parser.add_argument("action", choices=["setup", "info", "delete"], help="Action to perform")
    args = parser.parse_args()
    
    if args.action == "setup":
        asyncio.run(setup_webhook())
    elif args.action == "info":
        asyncio.run(get_webhook_info())
    elif args.action == "delete":
        asyncio.run(delete_webhook())
