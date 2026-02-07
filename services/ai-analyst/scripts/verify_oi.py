
import asyncio
import httpx
import json
import time
import os

API_URL = os.getenv("API_URL", "http://api-gateway:8000")

async def main():
    print("🚀 Starting Open Interest Verification...")
    
    async with httpx.AsyncClient() as client:
        # 1. Authentication
        print("\n🔐 Authenticating as trader1...")
        try:
            # Login
            login_resp = await client.post(
                f"{API_URL}/api/v1/auth/token",
                data={"username": "trader1@example.com", "password": "password123"}
            )
            if login_resp.status_code != 200:
                print(f"   ❌ Login Failed: {login_resp.status_code} - {login_resp.text}")
                return
            
            data = login_resp.json()
            if "auth" in data and "access_token" in data["auth"]:
                 token = data["auth"]["access_token"]
            elif "access_token" in data:
                 token = data["access_token"]
            else:
                 print(f"   ❌ Token not found in response: {data.keys()}")
                 return
            headers = {"Authorization": f"Bearer {token}"}
            print(f"   Logged in.")
        except Exception as e:
            print(f"❌ Auth Exception: {e}")
            return

        # 2. Test Open Interest Tool via Chat
        print("\n📊 Test: Open Interest Analysis")
        payload = {
            "message": "What is the Open Interest showing for XAUUSD?",
            "user_id": "trader1"
        }
        try:
            start = time.time()
            print("   Sending Request...")
            resp = await client.post(
                f"{API_URL}/api/v1/ai/chat/sessions/message", 
                json=payload, headers=headers, timeout=120.0
            )
            print(f"   Response Time: {time.time() - start:.2f}s")
            
            if resp.status_code == 200:
                answer = resp.json().get("response", "")
                print(f"   AI Response:\n{answer}")
                
                # Validation
                required_terms = ["Open Interest", "Net OI"]
                missing = [t for t in required_terms if t not in answer]
                
                if not missing:
                    print("   ✅ Open Interest data verified.")
                else:
                    print(f"   ⚠️ Missing data: {missing}")
                    
                if "Put/Call" in answer:
                    print("   ✅ Put/Call Ratio detected.")
            else:
                print(f"   ❌ Error: {resp.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
