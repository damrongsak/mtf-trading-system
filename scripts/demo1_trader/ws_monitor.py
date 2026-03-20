import asyncio
import websockets
import json
import requests
import logging

# --- Configuration ---
API_BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "demo1"
PASSWORD = "password123"
SYMBOLS = "XAU_USD,EUR_USD"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_token():
    """Get JWT Token via REST API"""
    url = f"{API_BASE_URL}/auth/token"
    resp = requests.post(url, data={"username": USERNAME, "password": PASSWORD})
    return resp.json()["auth"]["access_token"]

async def monitor_prices():
    """Real-time Price Monitor using WebSockets"""
    token = await get_token()
    uri = f"ws://localhost:8000/api/v1/stream/prices?symbols={SYMBOLS}&token={token}"
    
    logger.info(f"Connecting to WebSocket: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected! Monitoring {SYMBOLS}...")
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                # Format output
                symbol = data.get("symbol")
                bid = data.get("bid")
                ask = data.get("ask")
                ts = data.get("timestamp")
                
                print(f"[{ts}] {symbol:7} | BID: {bid:10.5f} | ASK: {ask:10.5f} | SPREAD: {(ask-bid)*100:.2f} pips")
                
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(monitor_prices())
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")
