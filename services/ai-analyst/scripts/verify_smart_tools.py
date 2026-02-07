import asyncio
import httpx
import json
import time
import os

# Configuration
API_URL = os.getenv("API_URL", "http://api-gateway:8000") # Use internal docker alias if inside container
# If running from host, might need localhost:8000
# But this script is usually run inside ai-analyst container via 'uv run'.

async def main():
    print("🚀 Starting Smart Tools Verification...")
    
    async with httpx.AsyncClient() as client:
        # 1. Authentication
        print("\n🔐 Authenticating...")
        # Use provided credentials
        user_id = "trader1"
        try:
            # Try to register (might fail if exists, that's fine)
            reg_resp = await client.post(
                f"{API_URL}/api/v1/auth/register",
                json={"username": "trader1@example.com", "email": "trader1@example.com", "password": "password123"}
            )
            if reg_resp.status_code == 200:
                print("   User Registered.")
            else:
                print(f"   ⚠️ Registration Failed: {reg_resp.status_code} - {reg_resp.text}")
            
            # Login
            login_resp = await client.post(
                f"{API_URL}/api/v1/auth/token",
                data={"username": "trader1@example.com", "password": "password123"}
            )
            if login_resp.status_code != 200:
                print(f"   ❌ Login Failed: {login_resp.status_code} - {login_resp.text}")
                return

            print(f"   Login Response Body: {login_resp.text}") # DEBUG
            
            data = login_resp.json()
            if "auth" in data and "access_token" in data["auth"]:
                 token = data["auth"]["access_token"]
            elif "access_token" in data:
                 token = data["access_token"]
            else:
                 print(f"   ❌ Token not found in response: {data.keys()}")
                 return
            headers = {"Authorization": f"Bearer {token}"}
            print(f"   Logged in as {user_id}")
        except Exception as e:
            print(f"❌ Auth Exception: {e}")
            return

        # 2. Test Market Data (Candles + News)
        print("\n📊 Test 1: Market Data (Candles + News)")
        payload = {
            "message": "Check XAUUSD price action (candles) and news.",
            "user_id": user_id
        }
        try:
            # We interact via the Chat API to test the AGENT's ability to use the tool
            start = time.time()
            print("   Sending Request...")
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message", 
                json=payload, headers=headers, timeout=120.0
            )
            print(f"   Response Time: {time.time() - start:.2f}s")
            
            if resp.status_code == 200:
                answer = resp.json().get("response", "")
                print(f"   AI Response Preview: {answer[:300]}...")
                
                # Validation
                if "Candles" in answer or "Price" in answer:
                    print("   ✅ Candles detected in response.")
                else:
                    print("   ⚠️ Candles missing.")
                    
                if "News" in answer or "Source" in answer:
                     print("   ✅ News detected in response.")
                else:
                     print("   ⚠️ News missing.")
            else:
                print(f"   ❌ Error: {resp.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        # 3. Test Python Sandbox
        print("\n🐍 Test 2: Python Sandbox")
        payload = {
            "message": "Calculate the average of simple numbers like [10, 20, 30, 40] using python.",
            "user_id": user_id
        }
        try:
            start = time.time()
            print("   Sending Request...")
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message", 
                json=payload, headers=headers, timeout=120.0
            )
            
            if resp.status_code == 200:
                answer = resp.json().get("response", "")
                print(f"   AI Response: {answer}")
                if "25" in answer:
                    print("   ✅ Calculation Correct (Mean is 25).")
                else:
                    print("   ⚠️ Calculation could not be verified.")
            else:
                 print(f"   ❌ Error: {resp.text}")
        except Exception as e:
             print(f"   ❌ Exception: {e}")

        # 4. Test Risk Check
        print("\n🛡️ Test 3: Risk Check (Pre-Trade)")
        payload = {
            "message": "I want to buy 100 lots of XAUUSD. Check risk.",
            "user_id": user_id
        }
        try:
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message", 
                json=payload, headers=headers, timeout=120.0
            )
            
            if resp.status_code == 200:
                answer = resp.json().get("response", "")
                print(f"   AI Response: {answer}")
                if "Risk Check" in answer or "High" in answer or "Failed" in answer or "confirm" in answer:
                     print("   ✅ Risk Awareness Detected.")
                else:
                     print("   ⚠️ Risk Check might have been skipped.")
            else:
                 print(f"   ❌ Error: {resp.text}")
        except Exception as e:
             print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
