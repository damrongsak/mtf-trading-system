import asyncio
import httpx
import json
import time

# Use the existing test token
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzczMjAxMzY2fQ.fWf02pRdWYYxTPknDVKUZ-wPBlhAS1SeCOhLYsvmTIY"
AI_ANALYST_URL = "http://0.0.0.0:8000/api/v1/ai/chat/sessions/message"

async def test_oi_thai_query():
    user_id = f"trader_oi_test_{int(time.time())}"
    payload = {
        "message": "explain about latest OI (show in Thai language)",
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
            
            if response.status_code != 200:
                print(f"❌ FAILED: Received status {response.status_code}")
                print(response.text)
                return

            result = response.json()
            ai_response = result.get("data", {}).get("response", "")
            print("\nAI Response:\n" + ai_response)
            
            # Check for Gold Context and Correct Data
            success_data = False
            success_context = False
            
            if "542,710" in ai_response or "0.658" in ai_response:
                success_data = True
            
            if "GOLD" in ai_response.upper() or "XAU" in ai_response.upper():
                success_context = True
                
            if "OIWAP" in ai_response:
                print("✅ OIWAP metric found in response.")
            else:
                print("⚠️ OIWAP metric NOT found.")

            if success_data and success_context:
                print("\n✅ VERIFICATION SUCCESSFUL: AI returned non-zero Open Interest values with GOLD context.")
            else:
                print(f"\n❌ VERIFICATION FAILED: Data={success_data}, Context={success_context}")
                
        except Exception as e:
            print(f"Verification Failed with Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_oi_thai_query())
