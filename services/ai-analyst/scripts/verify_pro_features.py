
import asyncio
import httpx
import os
import json
import time

# Configuration
API_URL = os.getenv("API_URL", "http://api-gateway:8000")
USERNAME = "admin"
PASSWORD = "password" # From earlier logs

async def verify_chat():
    async with httpx.AsyncClient() as client:
        # 1. Register/Login (Use fresh user to avoid Auth issues)
        print("Registering new test user...")
        import uuid
        test_user = f"test_pro_{int(time.time())}"
        test_pass = "password123"
        test_email = f"{test_user}@example.com"
        
        try:
            resp = await client.post(
                f"{API_URL}/api/v1/auth/register",
                json={"username": test_user, "email": test_email, "password": test_pass}
            )
            
            if resp.status_code == 200:
                data = resp.json()["data"]
                auth = resp.json().get("auth", {})
                token = auth.get("access_token")
                user_id = data["id"]
                print(f"Registered & Logged in as {test_user}")
            else:
                print(f"Registration failed ({resp.status_code}): {resp.text}")
                # Fallback to login if somehow conflict, though timestamp makes unique
                return
                
        except Exception as e:
            print(f"Auth Error: {e}")
            return
        except Exception as e:
            print(f"Login Error: {e}")
            return

        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Market Analysis (SMC) - Read Only capability
        # print("\n--- Test 1: Market Analysis (SMC) ---")
        # payload = {
        #     "message": "Analyze Gold (XAUUSD) using SMC. Tell me the story of price.",
        #     "user_id": user_id
        # }
        # start = time.time()
        # resp = await client.post(f"{API_URL}/api/v1/ai/chat/sessions/message", json=payload, headers=headers, timeout=120.0)
        # print(f"Response Time: {time.time() - start:.2f}s")
        # if resp.status_code == 200:
        #     print(f"AI: {resp.json().get('response')}")
        # else:
        #     print(f"Error: {resp.text}")

        # Test 2: Execution Confirmation (Safety Check)
        print("\n--- Test 2: Execution Confirmation ---")
        payload = {
            "message": "Place a BUY order for XAUUSD, risk 100 USD.",
            "user_id": user_id
        }
        resp = await client.post(f"{API_URL}/api/v1/ai/chat/sessions/message", json=payload, headers=headers, timeout=120.0)
        response_text = resp.json().get('response', '')
        print(f"AI: {response_text}")
        
        if "Confirmation Required" in response_text or "confirm" in response_text.lower():
            print("✅ Confirmation Triggered Correctly.")
            
            # Test 3: Confirming the Action
            print("\n--- Test 3: Confirming Action ---")
            payload = {
                "message": "YES",
                "user_id": user_id
            }
            resp = await client.post(f"{API_URL}/api/v1/ai/chat/sessions/message", json=payload, headers=headers, timeout=120.0)
            print(f"AI: {resp.json().get('response')}")
        else:
            print("❌ Confirmation NOT Triggered.")

if __name__ == "__main__":
    asyncio.run(verify_chat())
