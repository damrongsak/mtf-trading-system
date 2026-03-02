import httpx
import asyncio
import json
import uuid
import sys

BASE_URL = "http://api-gateway:8000/api/v1"
# Login credentials from user
AUTH_DATA = {"username": "trader1", "password": "password123"}

async def run_e2e_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("--- 1. Authentication ---")
        login_resp = await client.post(f"{BASE_URL}/auth/token", data=AUTH_DATA)
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.text}")
            return
        
        # Correctly extract token from nested auth field
        auth_data = login_resp.json().get("auth", {})
        token = auth_data.get("access_token")
        if not token:
            print(f"❌ Token not found in response: {login_resp.json()}")
            return
            
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful")

        print("\n--- 2. Account Summary (New/Fixed Endpoint) ---")
        summary_resp = await client.get(f"{BASE_URL}/execution/account/summary", headers=headers)
        print(f"GET /execution/account/summary: {summary_resp.status_code}")
        if summary_resp.status_code == 200:
            data = summary_resp.json().get("data", {})
            acc_id = data.get("id") or data.get("account_id")
            if acc_id:
                summary_id_resp = await client.get(f"{BASE_URL}/execution/accounts/{acc_id}/summary", headers=headers)
                print(f"GET /execution/accounts/{{id}}/summary: {summary_id_resp.status_code}")
        else:
            print(f"Response: {summary_resp.text}")
        
        print("\n--- 3. Symbol Normalization Test ---")
        signal_resp = await client.get(f"{BASE_URL}/signal/latest/XAU/USD", params={"timeframe": "H1"}, headers=headers)
        print(f"GET /signal/latest/XAU/USD: {signal_resp.status_code}")
        
        print("\n--- 4. Execution Error Handling (404 Test) ---")
        fake_id = "999999"
        dummy_acc_id = str(uuid.uuid4())
        amend_resp = await client.post(
            f"{BASE_URL}/execution/trades/{fake_id}/amend", 
            json={"broker_account_id": dummy_acc_id, "stop_loss": 2000.0}, 
            headers=headers
        )
        print(f"POST /execution/trades/{{fake}}/amend: {amend_resp.status_code}")
        print(f"Response: {amend_resp.text}")

        print("\n--- 5. AI Analyst Tool Parsing Test ---")
        # Use valid schema for MarketAnalysisRequest
        ai_payload = {
            "trend_4h": "BULLISH",
            "current_price": 2000.0,
            "key_levels": [1980.0, 2020.0],
            "recent_signals": [{"direction": "BUY", "price": 1990.0}]
        }
        ai_resp = await client.post(
            f"{BASE_URL}/ai/market-analysis", 
            json=ai_payload, 
            headers=headers
        )
        print(f"POST /ai/market-analysis: {ai_resp.status_code}")
        if ai_resp.status_code == 200:
            print("✅ AI Analysis successful")
        else:
            print(f"Response: {ai_resp.text}")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
