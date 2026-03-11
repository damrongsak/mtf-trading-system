import asyncio
import httpx
import json
import os

BASE_URL = "http://localhost:8000/api/v1/ai/think" # Assuming internal port or through Gateway
# Actually, inside the container, we might need to hit the ai-analyst internal port
AI_ANALYST_URL = "http://127.0.0.1:8000/api/v1/ai/think" 

async def test_ai_think(message, intent=None):
    payload = {
        "message": message,
        "intent": intent,
        "context": {"symbol": "XAUUSD"}
    }
    
    print(f"\n[Testing] Message: {message}")
    async with httpx.AsyncClient() as client:
        try:
            # First check health
            health = await client.get("http://127.0.0.1:8000/health")
            print(f"Health Check: {health.status_code} - {health.text[:50]}")
            
            headers = {"Authorization": "Bearer internal_test_token"}
            response = await client.post(AI_ANALYST_URL, json=payload, headers=headers, timeout=60.0)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success! Status: {data.get('status')}")
                print(f"Intent Resolved: {data.get('data', {}).get('intent_resolved')}")
                print(f"Severity: {data.get('data', {}).get('severity')}")
                print(f"Response: {data.get('data', {}).get('response')[:100]}...")
            else:
                print(f"Failed! Status Code: {response.status_code}")
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

async def main():
    # 1. Routine
    await test_ai_think("Hello, system status check.")
    
    # 2. Market Analysis (Intended for MarketObserver)
    await test_ai_think("What's the current trend for XAUUSD?", intent="analysis")
    
    # 3. Crisis (Intended for StrategyAdvisor/CRISIS)
    await test_ai_think("Urgently review my risk on XAUUSD, market is moving fast!")

if __name__ == "__main__":
    asyncio.run(main())
