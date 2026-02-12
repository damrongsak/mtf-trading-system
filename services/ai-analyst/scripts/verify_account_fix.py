import asyncio
import httpx
import json
import time

# Use the existing test token from trader1
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzczMjAxMzY2fQ.fWf02pRdWYYxTPknDVKUZ-wPBlhAS1SeCOhLYsvmTIY"
AI_ANALYST_URL = "http://localhost:8000/api/v1/ai/chat/sessions/message"

async def test_account_balance_conversion():
    user_id = f"trader_diagnose_{int(time.time())}"
    payload = {
        "message": "What is my account balance? Please convert it to its value in XAUUSD units based on current market price.",
        "user_id": user_id
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Sending request to AI Analyst: {AI_ANALYST_URL}")
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(AI_ANALYST_URL, json=payload, headers=headers)
            print(f"Status: {response.status_code}")
            result = response.json()
            ai_response = result.get("data", {}).get("response", "")
            print("\nAI Response:\n" + ai_response)
            
            # Check for error keywords
            if "connection error" in ai_response.lower() or "unable" in ai_response.lower() and "balance" in ai_response.lower():
                print("\n❌ VERIFICATION FAILED: Error message still present in AI response.")
            else:
                print("\n✅ VERIFICATION SUCCESSFUL: AI successfully retrieved balance.")
                
        except Exception as e:
            print(f"Verification Failed with Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_account_balance_conversion())
