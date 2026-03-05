import asyncio
import websockets
import json
import time
import hmac
import hashlib
import sys

# Test Credentials (Seeded via seed_test_api_key.py)
API_KEY = "test_api_key_123"
API_SECRET = "test_secret_456"
# Use 127.0.0.1 for internal container testing if needed, or service name
WS_URL = "ws://127.0.0.1:8000/api/v1/external/ws/command"

def generate_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    payload = f"{timestamp}{method}{path}{body}"
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

async def test_ws():
    timestamp = str(time.time())
    path = "/api/v1/external/ws/command"
    method = "GET"
    
    signature = generate_signature(API_SECRET, timestamp, method, path)
    
    url = f"{WS_URL}?api_key={API_KEY}&signature={signature}&timestamp={timestamp}"
    
    print(f"Connecting to {url}...")
    
    try:
        async with websockets.connect(url) as websocket:
            # 1. Receive Welcome Message
            welcome = await websocket.recv()
            print(f"Received Welcome: {welcome}")
            
            # 2. Send get_account command
            cmd = {
                "cmd": "get_account",
                "id": "req_001",
                "params": {
                    "broker_account_id": "2c542d2a-b151-41e0-8cc0-8f0ca2a3eb49" # MOCK Account from DB
                }
            }
            await websocket.send(json.dumps(cmd))
            print(f"Sent command: {cmd}")
            
            # 3. Receive Response
            resp = await websocket.recv()
            print(f"Received Response: {resp}")
            
            # 4. Send execute command (Mock Account)
            cmd_exec = {
                "cmd": "execute",
                "id": "req_002",
                "params": {
                    "broker_account_id": "2c542d2a-b151-41e0-8cc0-8f0ca2a3eb49",
                    "symbol": "XAU_USD",
                    "units": 1000,
                    "direction": "BULLISH",
                    "order_type": "MARKET"
                }
            }
            await websocket.send(json.dumps(cmd_exec))
            print(f"Sent execute command: {cmd_exec}")
            
            resp_exec = await websocket.recv()
            print(f"Received Execute Response: {resp_exec}")
            
    except Exception as e:
        print(f"Error during WS test: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_ws())
