#!/usr/bin/env python3
"""
XAUUSD Signal Monitor - Olympus API
==========================================
Gets signals from Olympus API and sends to Telegram.
Refactored for robustness, async/await, and environment-based config.

Author: Soda / Antigravity
Date: 2026-03-02
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

import httpx

# ============= CONFIG =============
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_URL = os.getenv("API_URL", "http://localhost:8000")
USERNAME = os.getenv("USERNAME", "trader1")
PASSWORD = os.getenv("PASSWORD", "password123")
SYMBOL = os.getenv("SYMBOL", "XAUUSD")

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("xauusd-monitor")

class OlympusClient:
    """
    Client for interacting with Olympus API.
    """
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=10.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def authenticate(self) -> bool:
        """
        Authenticate with the Olympus API and store the token.
        """
        logger.info(f"Authenticating with {self.api_url} as {USERNAME}...")
        try:
            resp = await self.client.post(
                f"{self.api_url}/api/v1/auth/token",
                data={"username": USERNAME, "password": PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data['auth']['access_token']
            self.user_id = data['data']['id']
            logger.info(f"Successfully authenticated. User ID: {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def get_latest_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Get the latest signal for a specific symbol.
        """
        if not self.token:
            raise ValueError("Not authenticated")

        logger.info(f"Fetching latest signal for {symbol}...")
        try:
            resp = await self.client.get(
                f"{self.api_url}/api/v1/signal/latest/{symbol}",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch signal: {e}")
            return {"status": "error", "message": str(e)}

    async def send_telegram_message(self, message: str) -> Dict[str, Any]:
        """
        Send a message via Olympus Telegram service.
        """
        if not self.token:
            raise ValueError("Not authenticated")

        logger.debug(f"Sending Telegram message...")
        try:
            resp = await self.client.post(
                f"{self.api_url}/api/v1/telegram/send",
                json={"message": message},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return {"status": "error", "message": str(e)}

def format_signal(signal_response: Dict[str, Any], symbol: str) -> str:
    """
    Format signal data into a readable Telegram message.
    """
    data = signal_response.get('data', {})
    
    direction = "🟢 LONG" if data.get('direction') == 'LONG' else "🔴 SHORT"
    entry = data.get('entry_price', 'N/A')
    sl = data.get('sl_price', 'N/A')
    tp = data.get('tp_price', 'N/A')
    reason = data.get('reason', 'No reason provided')
    strategy = data.get('strategy_name', 'Unknown Strategy')
    timeframe = data.get('timeframe', 'Unknown TF')
    freshness = data.get('data_freshness', 'Unknown freshness')
    
    msg = (
        f"{direction} {symbol} {timeframe}\n\n"
        f"Entry: {entry}\n"
        f"SL:    {sl}\n"
        f"TP:    {tp}\n\n"
        f"📝 {reason}\n\n"
        f"Strategy: {strategy}\n"
        f"Data: {freshness}\n\n"
        f"⏰ {datetime.now().strftime('%H:%M %d/%m')}"
    )
    return msg

async def main():
    logger.info("=" * 40)
    logger.info("XAUUSD Signal Monitor Starting")
    logger.info("=" * 40)
    
    async with OlympusClient(API_URL) as client:
        if not await client.authenticate():
            logger.error("Exiting due to authentication failure.")
            return

        # Get latest signal
        signal_data = await client.get_latest_signal(SYMBOL)
        
        if signal_data.get('status') == 'success':
            data = signal_data.get('data', {})
            
            if data.get('direction'):
                # We have a valid signal
                message = format_signal(signal_data, SYMBOL)
                result = await client.send_telegram_message(message)
                
                if result.get('status') == 'success':
                    logger.info("Signal successfully relayed to Telegram.")
                    print(f"\n{message}\n")
                else:
                    logger.error(f"Failed to relay signal: {result}")
            else:
                # No active signal
                logger.info("No active signal found.")
                status_msg = f"🔔 {SYMBOL}\n\nNo active signal."
                await client.send_telegram_message(status_msg)
        else:
            logger.error(f"API Error: {signal_data.get('message', 'Unknown error')}")
    
    logger.info("Monitor task completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
