import hmac
import hashlib
import time
import requests
import json
import asyncio
import websockets
from typing import List, Callable

class MTFOlympusPartnerClient:
    """
    REST Client for MTF Olympus External Gateway.
    Handles HMAC-SHA256 signing for all requests.
    """
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret

    def _generate_signature(self, method: str, path: str, timestamp: str, body: str = "") -> str:
        payload = f"{timestamp}{method.upper()}{path}{body}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def request(self, method: str, path: str, data: dict = None):
        timestamp = str(int(time.time()))
        body_str = json.dumps(data) if data else ""
        
        # Ensure path starts with /
        if not path.startswith("/"): path = "/" + path
        
        signature = self._generate_signature(method, path, timestamp, body_str)
        
        headers = {
            "X-API-KEY": self.api_key,
            "X-TIMESTAMP": timestamp,
            "X-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
        
        response = requests.request(method, f"{self.base_url}{path}", headers=headers, data=body_str)
        return response.json()

class MTFOlympusStream:
    """
    WebSocket Client for Real-time Market Data.
    Uses HMAC-SHA256 via Query Parameters for handshake.
    """
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        # Convert http:// -> ws://
        self.ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret

    def _generate_ws_signature(self, path: str, timestamp: str) -> str:
        # WebSocket Handshake is always a GET request with no body
        payload = f"{timestamp}GET{path}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def listen(self, symbols: List[str], callback: Callable):
        timestamp = str(int(time.time()))
        path = "/api/v1/external/ws/prices"
        signature = self._generate_ws_signature(path, timestamp)
        
        # Construct authenticated URL
        params = [
            f"api_key={self.api_key}",
            f"timestamp={timestamp}",
            f"signature={signature}",
            f"symbols={','.join(symbols)}"
        ]
        auth_url = f"{self.ws_url}{path}?{'&'.join(params)}"
        
        print(f"🔌 Connecting to Stream: {symbols}...")
        async with websockets.connect(auth_url) as ws:
            print("✅ Connected. Receiving live data...")
            while True:
                message = await ws.recv()
                data = json.loads(message)
                callback(data)

# --- Example Usage for AI Agent ---

async def main():
    # 1. Configuration
    CONFIG = {
        "base_url": "http://localhost:8000",
        "api_key": "ak_live_...", # Insert your key from Dashboard
        "api_secret": "sk_live_..." # Insert your secret
    }

    client = MTFOlympusPartnerClient(**CONFIG)
    stream = MTFOlympusStream(**CONFIG)

    # 2. REST API: Get Market Snapshot (O(1) from Redis)
    print("\n[REST] Fetching Snapshot...")
    snapshot = client.request("GET", "/api/v1/external/market/snapshot/XAUUSD")
    print(f"Result: {snapshot}")

    # 3. REST API: Execute Trade
    print("\n[REST] Executing Trade...")
    trade_res = client.request("POST", "/api/v1/external/trade/execute", data={
        "symbol": "XAU_USD",
        "direction": "LONG",
        "risk_usd": 5.0
    })
    print(f"Result: {trade_res}")

    # 4. WebSocket: Live Streaming
    def on_price_update(data):
        print(f"⚡ Live Price | {data['symbol']}: {data['bid']} / {data['ask']}")

    try:
        await stream.listen(["XAUUSD", "EURUSD"], on_price_update)
    except Exception as e:
        print(f"❌ Stream Error: {e}")

if __name__ == "__main__":
    # Note: Requires 'requests' and 'websockets' libraries
    # pip install requests websockets
    asyncio.run(main())
