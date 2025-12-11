import asyncio
import websockets
import json
import sys

# Default URL - adjust if your API Gateway is running elsewhere
WS_URL = "ws://localhost:8000/api/v1/stream/prices?symbols=EUR_USD,XAU_USD,GBP_USD"

async def test_connection():
    print(f"Connecting to {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected successfully!")
            print("Waiting for price updates (Press Ctrl+C to stop)...")
            print("-" * 50)
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'PRICE':
                    # Format output nicely
                    symbol = data.get('instrument', 'UNKNOWN')
                    bid = data.get('bid', 0.0)
                    ask = data.get('ask', 0.0)
                    time = data.get('time', '').split('T')[1].split('.')[0]
                    print(f"[{time}] {symbol:<8} | Bid: {bid:.5f} | Ask: {ask:.5f}")
                else:
                    print(f"Received: {message}")
                    
    except ConnectionRefusedError:
        print("❌ Connection failed. Is the API Gateway running?")
        print("Try running: docker compose up api-gateway strategy-core")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print("\nStopping...")
