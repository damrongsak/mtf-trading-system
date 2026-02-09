import asyncio
import httpx
import json
import time

# Use the existing test token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzczMjAxMzY2fQ.fWf02pRdWYYxTPknDVKUZ-wPBlhAS1SeCOhLYsvmTIY"
AI_ANALYST_URL = "http://localhost:8000/api/v1/ai/chat/sessions/message"

async def test_multi_tool_trade_plan():
    user_id = f"trader_pro_multi_test_{int(time.time())}"
    payload = {
        "message": "plan trade for XAUUSD on M5 timeframe and send a professional summary to my telegram using the send_notification tool.",
        "user_id": user_id
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Sending request to AI Analyst: {AI_ANALYST_URL} for User: {user_id}")
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(AI_ANALYST_URL, json=payload, headers=headers)
            print(f"Status: {response.status_code}")
            print("AI Response:")
            print(json.dumps(response.json(), indent=2))
        except Exception as e:
            print(f"Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_multi_tool_trade_plan())
