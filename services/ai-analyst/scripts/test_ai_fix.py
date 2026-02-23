import asyncio
import httpx
import os

API_URL = os.environ.get("API_URL", "http://api-gateway:8000")
USER_CREDENTIALS = {"username": "trader1", "password": "password123"}

async def test_fix():
    print("🚀 Verifying AI Fixes...")
    
    async with httpx.AsyncClient() as client:
        # 1. Auth
        resp = await client.post(f"{API_URL}/api/v1/auth/token", data=USER_CREDENTIALS)
        resp.raise_for_status()
        auth_data = resp.json()
        token = auth_data["auth"]["access_token"]
        user_id = auth_data["data"]["id"]
        
        # 2. Test Query (Risky + Tool Use)
        # This query triggers the specific 'ToolCall' schema node and tests safety.
        query = "If I trade Gold at 2150 with a $2000 stop, what is the lot size for a $10M fund at 1% risk?"
        
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Query: {query}")
        
        try:
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message",
                json={"message": query, "user_id": user_id},
                headers=headers,
                timeout=60.0
            )
            
            if resp.status_code == 200:
                data = resp.json()["data"]
                print("✅ PASSED: AI responded successfully.")
                print(f"Response: {data.get('response')[:200]}...")
            else:
                print(f"❌ FAILED: Status {resp.status_code}")
                print(f"Output: {resp.text}")
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(test_fix())
