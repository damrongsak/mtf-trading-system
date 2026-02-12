import asyncio
import httpx
import json
import os
from tabulate import tabulate
from app.core.bootstrap import bootstrap_tools, run_diagnostics
from app.core.config import settings

# Test Credentials provided by USER
USER_EMAIL = "trader1@example.com"
USER_PASS = "password123"
API_URL = os.getenv("API_URL", "http://api-gateway:8000")

async def get_token():
    print(f"🔐 Authenticating as {USER_EMAIL} (Username: trader1)...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Ensure user exists
            await client.post(
                f"{API_URL}/api/v1/auth/register",
                json={"username": "trader1", "email": USER_EMAIL, "password": USER_PASS}
            )
            
            # 2. Login - The auth/token endpoint often expects 'username' as form field, not email.
            # In many systems, the username is extracted from the form 'username' field.
            resp = await client.post(
                f"{API_URL}/api/v1/auth/token",
                data={"username": "trader1", "password": USER_PASS}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                token = None
                if "auth" in data and "access_token" in data["auth"]:
                    token = data["auth"]["access_token"]
                else:
                    token = data.get("access_token")
                
                if token:
                    print(f"✅ Auth Successful (Token: {token[:10]}...)")
                    return token
                else:
                    print(f"❌ Auth Succeeded but no token found in: {data.keys()}")
                    return None
            else:
                print(f"❌ Auth Failed: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            import traceback
            print(f"❌ Auth Exception: {e}")
            traceback.print_exc()
            return None

async def main():
    print("🚀 Starting AI Tool System Diagnostic...")
    print("-" * 50)
    
    # 1. Bootstrap Registry
    bootstrap_tools()
    
    # 2. Get Token
    token = await get_token()
    if not token:
        print("⚠️ Proceeding without token (Account-dependent tools will fail)")
    
    # 3. Run Diagnostics
    print("\n🔍 Running Smoke Tests...")
    results = await run_diagnostics(auth_token=token)
    
    # 4. Display Results
    table_data = []
    for r in results:
        status_emoji = "✅" if r["status"] == "SUCCESS" else "❌" if r["status"] == "ERROR" else "⚠️" if r["status"] == "FAILED" else "⏭️"
        table_data.append([status_emoji, r["tool"], r["status"], r["message"]])
    
    print("\n" + tabulate(table_data, headers=["", "Tool Name", "Status", "Details"], tablefmt="grid"))
    
    # 5. Summary
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    print(f"\n✨ Diagnostic Complete: {success_count}/{len(results)} tools passed.")

if __name__ == "__main__":
    asyncio.run(main())
