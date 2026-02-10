import asyncio
import httpx
import json

async def verify():
    # Use api-gateway internal URL
    base_url = "http://api-gateway:8000/api/v1/signal"
    symbol = "XAUUSD"
    
    print(f"--- Verifying Market State for {symbol} ---")
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"{base_url}/market-state/{symbol}"
            print(f"Calling: {url}")
            resp = await client.get(url, timeout=30.0)
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print("Response Data:")
                print(json.dumps(data, indent=2))
                
                # Check for key features
                analysis = data.get("data", {})
                required = ["volatility_regime", "trend_structure", "is_squeeze", "vwap_distance_percent"]
                missing = [k for k in required if k not in analysis]
                
                if not missing:
                    print("\n✅ All core sensory features present!")
                else:
                    print(f"\n❌ Missing features: {missing}")
            else:
                print(f"Error: {resp.text}")
                
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
