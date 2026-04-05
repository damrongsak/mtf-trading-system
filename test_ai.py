import asyncio
import httpx
import json

async def run():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Login
        login_res = await client.post(
            "http://api-gateway:8000/api/v1/auth/token",
            data={"username": "demo1", "password": "password123"}
        )
        if login_res.status_code != 200:
            print("Login failed:", login_res.text)
            return

        token = login_res.json()["auth"]["access_token"]
        print("Logged in successfully.")

        # 2. Chat with AI Analyst
        chat_req = {
            "session_id": "test_ai_sim_1",
            "message": "Calculate the RSI (window 7) and EMA (span 50) for XAUUSD on M15 timeframe using your technical indicators tool."
        }
        print("Sending chat request:", chat_req)
        
        chat_res = await client.post(
            "http://api-gateway:8000/api/v1/ai/chat/sessions/message",
            json=chat_req,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status: {chat_res.status_code}")
        print("Response:", json.dumps(chat_res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(run())
