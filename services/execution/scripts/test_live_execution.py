import asyncio
import os
import uuid
import sys
import httpx
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000/api/v1")
USERNAME = "trader1"
PASSWORD = "password123"
SYMBOL = "XAUUSD"
LOTS = 0.01

class LiveTester:
    def __init__(self):
        self.token = None
        self.account_id = None
        self.position_id = None

    async def authenticate(self):
        logger.info(f"Authenticating as {USERNAME}...")
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{API_BASE_URL}/auth/token", data={"username": USERNAME, "password": PASSWORD})
            if res.status_code == 200:
                self.token = res.json().get("auth", {}).get("access_token")
                logger.info("Authentication successful.")
            else:
                logger.error(f"Auth failed: {res.status_code} - {res.text}")
                sys.exit(1)

    async def get_account(self):
        logger.info("Fetching cTrader account...")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{API_BASE_URL}/execution/accounts", headers=headers)
            if res.status_code == 200:
                accounts = res.json().get("data", [])
                ctrader_acc = next((a for a in accounts if a["broker_name"] == "CTRADER"), None)
                if ctrader_acc:
                    self.account_id = ctrader_acc["id"]
                    logger.info(f"Found account: {self.account_id}")
                else:
                    logger.error("No cTrader account found.")
                    sys.exit(1)
            else:
                logger.error(f"Failed to fetch accounts: {res.text}")
                sys.exit(1)

    async def place_market_order(self):
        logger.info(f"Placing live MARKET BUY order for {LOTS} lots of {SYMBOL}...")
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "broker_account_id": self.account_id,
            "trade_id": str(uuid.uuid4()),
            "symbol": SYMBOL,
            "order_type": "MARKET",
            "units": float(LOTS * 100), # cTrader XAUUSD 1 lot = 100 units
            "side": "BUY"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{API_BASE_URL}/execution/orders", json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json().get("data", {})
                self.position_id = data.get("position_id")
                logger.info(f"Order placed successfully. Position ID: {self.position_id}")
            else:
                logger.error(f"Order failed: {res.status_code} - {res.text}")
                sys.exit(1)

    async def verify_persistence(self):
        logger.info("Waiting 10s for trade persistence and reconciliation...")
        await asyncio.sleep(10)
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{API_BASE_URL}/execution/trades", params={"broker_account_id": self.account_id}, headers=headers)
            if res.status_code == 200:
                trades = res.json().get("data", [])
                trade = next((t for t in trades if t.get("broker_trade_id") == self.position_id), None)
                if trade:
                    logger.info(f"✅ Trade {self.position_id} verified in database.")
                else:
                    logger.warning(f"⚠️ Trade {self.position_id} not found in database yet. Might still be syncing.")
            else:
                logger.error(f"Failed to fetch trades: {res.text}")

    async def close_position(self):
        if not self.position_id:
            return
        logger.info(f"Closing position {self.position_id}...")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            # We use DELETE on the positions endpoint to close
            res = await client.delete(f"{API_BASE_URL}/execution/positions/{self.position_id}", params={"broker_account_id": self.account_id}, headers=headers)
            if res.status_code == 200:
                logger.info(f"✅ Position {self.position_id} closed successfully.")
            else:
                logger.error(f"Failed to close position: {res.status_code} - {res.text}")

async def main():
    tester = LiveTester()
    await tester.authenticate()
    await tester.get_account()
    
    try:
        await tester.place_market_order()
        await tester.verify_persistence()
    finally:
        if tester.position_id:
            logger.info("Waiting 5s before closing for safety...")
            await asyncio.sleep(5)
            await tester.close_position()

if __name__ == "__main__":
    asyncio.run(main())
