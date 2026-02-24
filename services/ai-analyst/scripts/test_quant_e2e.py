import asyncio
import os
import httpx
from datetime import datetime
import json

API_URL = os.getenv("API_URL", "http://localhost:8000")
LOGIN_ENDPOINT = "/api/v1/auth/token"
AGENT_ENDPOINT = "/api/v1/ai/chat/sessions/message"

AI_QUESTIONS = [
    "Give me the institutional Risk Map for XAUUSD M15.",
    "Analyze XAUUSD H4 structural risk and volatility regime.",
    "Generate a trading plan for XAUUSD M15.",
    "Calculate a 1% risk position size based on the current market state for XAUUSD M15 with entry 2400 and SL 2380.",
    "Does the quant risk map support a long position on XAUUSD right now?"
]

API_SAMPLES = [
    ("POST", "/api/v1/quant/analyze", {"symbol": "XAUUSD", "timeframe": "M15"}),
    ("POST", "/api/v1/quant/analyze", {"symbol": "BTCUSD", "timeframe": "H1"}),
    ("POST", "/api/v1/quant/size", {"symbol": "XAUUSD", "entry_price": 2400.0, "stop_loss": 2390.0, "equity": 10000}),
    ("POST", "/api/v1/quant/size", {"symbol": "XAUUSD", "entry_price": 2400.0, "stop_loss": 2300.0, "equity": 100000, "timeframe": "H4"}),
    ("POST", "/api/v1/quant/size", {"symbol": "ETHUSD", "entry_price": 3000.0, "stop_loss": 2900.0, "equity": 50000})
]

async def run_e2e():
    print("🚀 Starting Quant Layer E2E Tests")
    async with httpx.AsyncClient(timeout=180.0) as client:
        # 1. Login
        print("\n🔑 Logging in as 'trader1'...")
        resp = await client.post(
            f"{API_URL}{LOGIN_ENDPOINT}",
            data={"username": "trader1", "password": "password123"}
        )
        if resp.status_code != 200:
            print(f"❌ Login failed: {resp.status_code}")
            return
        
        token_data = resp.json()
        token = token_data.get("access_token") or token_data.get("auth", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Login successful.")

        print("\n--- Running 5 API Sample Tests ---")
        for i, (method, endpoint, payload) in enumerate(API_SAMPLES, 1):
            url = f"{API_URL}{endpoint}"
            try:
                if method == "POST":
                    r = await client.post(url, json=payload, headers=headers)
                print(f"[{i}/5] {endpoint} with {payload['symbol']} -> Status: {r.status_code}")
                if r.status_code == 200:
                    data = r.json()
                    # print snippet
                    print(f"   Success: {str(data)[:100]}...")
                else:
                    print(f"   Failed: {r.text}")
            except Exception as e:
                print(f"[{i}/5] Error: {e}")

        session_id = f"quant_e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n--- Running 5 AI Question Tests (Session: {session_id}) ---")
        for i, q in enumerate(AI_QUESTIONS, 1):
            payload = {
                "message": q,
                "user_id": "trader1",
                "thread_id": session_id
            }
            try:
                print(f"\n[{i}/5] Ask: {q}")
                r = await client.post(f"{API_URL}{AGENT_ENDPOINT}", json=payload, headers=headers)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    answer = data.get("response", "")
                    print(f"✅ AI Answer length: {len(answer)}")
                    print(f"Snippet: {answer[:150]}...")
                else:
                    print(f"❌ AI Error {r.status_code}: {r.text}")
            except Exception as e:
                print(f"❌ AI Exception: {e}")

if __name__ == "__main__":
    asyncio.run(run_e2e())
