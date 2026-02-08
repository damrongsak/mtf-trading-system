
import asyncio
import httpx
import json
import os
import sys

API_URL = os.getenv("API_URL", "http://api-gateway:8000")

async def main():
    print("🚀 Starting Weekly Report Scenario Verification...")
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("🔐 Authenticating...")
        try:
            # User provided: trader1 / password123
            resp = await client.post(f"{API_URL}/api/v1/auth/token", data={"username": "trader1", "password": "password123"})
            if resp.status_code != 200:
                print(f"❌ Login Failed ({resp.status_code}): {resp.text}")
                return
            token = resp.json()["auth"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Authenticated as trader1")
        except Exception as e:
            print(f"❌ Auth Error: {type(e).__name__} - {e}")
            return

        # 2. Send Prompt
        prompt = "step-by-step breakdown of last week's gold market performance and the key events that drove its price action."
        print(f"\n📝 Prompt: '{prompt}'")
        
        start_time = asyncio.get_event_loop().time()
        try:
            print(f"⏳ Sending request to {API_URL} (Timeout: 180s)...")
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message", 
                json={"message": prompt, "user_id": "trader1"},
                headers=headers,
                timeout=180.0
            )
            elapsed = asyncio.get_event_loop().time() - start_time
            print(f"⏱️ Response Time: {elapsed:.2f}s")
            
            if resp.status_code == 200:
                data = resp.json()
                thoughts = data.get("thoughts", "")
                response = data.get("response", "")
                
                print("\n🧠 THOUGHTS (Reasoning Trace):")
                print("-" * 40)
                print(thoughts)
                print("-" * 40)
                
                print("\n🤖 RESPONSE:")
                print("-" * 40)
                print(response)
                print("-" * 40)
                
                # Check for evidence of date filtering in thoughts OR response
                # Calculate expected "Last Week" dates for 2026-02-08
                # Last Week = Monday Feb 2 to Sunday Feb 8 (or Feb 6 for trading week)
                
                evidence_found = False
                keywords = ["from_date", "to_date", "2026-02-02", "2026-02-06", "Feb 2", "Feb 02", "Feb 6", "Feb 06"]
                
                check_text = (thoughts + response).lower()
                
                found_keys = [k for k in keywords if k.lower() in check_text]
                
                if found_keys:
                     print(f"\n✅ Evidence of Date Filtering found: {found_keys}")
                else:
                     print("\n⚠️ NO evidence of Date Filtering found in output.")
                     print("Debug - Expected content like '2026-02-02', 'Feb 2', etc.")

            else:
                print(f"❌ Error ({resp.status_code}): {resp.text}")
                
        except Exception as e:
            print(f"❌ Request Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(main())
