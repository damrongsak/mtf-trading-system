import httpx
import asyncio
import sys
import json

async def test_drawdown():
    # 1. Get Token
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://api-gateway:8000/api/v1/auth/token",
            data={"username": "trader1", "password": "password123"}
        )
        if r.status_code != 200:
            print(f"Auth Error: {r.text}")
            return
        
        token = r.json().get("access_token")
        if not token and "auth" in r.json():
            token = r.json()["auth"]["access_token"]

    # 2. Test Drawdown Query
    payload = {
        "message": "What is the max drawdown risk based on current market volatility?",
        "user_id": "trader1",
        "thread_id": "drawdown-test-fix"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print(">>> Testing Drawdown Query (with optimized routing)...")
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            "http://api-gateway:8000/api/v1/ai/chat/sessions/message",
            json=payload,
            headers=headers
        )
        
        if r.status_code == 200:
            data = r.json()
            response = data.get("data", {}).get("response", "")
            thoughts = data.get("data", {}).get("thoughts", "")
            
            print("\n--- REASONING ---")
            print(thoughts)
            print("\n--- RESPONSE ---")
            print(response)
        else:
            print(f"API ERROR {r.status_code}: {r.text}")

if __name__ == "__main__":
    asyncio.run(test_drawdown())
