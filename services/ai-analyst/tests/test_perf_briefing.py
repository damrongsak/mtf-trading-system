
import asyncio
import time
import httpx
import json
import os

API_URL_BRIEFING = "http://localhost:8000/api/v1/ai/agent/briefing"
API_URL_CHAT = "http://localhost:8000/api/v1/ai/chat/sessions/message"
AUTH_TOKEN = os.getenv("AUTH_TOKEN") 

async def test_briefing_performance(mode="full"):
    print(f"\n--- Testing Briefing Performance (Mode: {mode}) ---")
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    
    url = API_URL_CHAT
    if mode == "full":
        payload = {
            "message": "Generate a full daily briefing",
            "user_id": "test_perf_user"
        }
    else:
        payload = {
            "message": "Give me a slim briefing",
            "user_id": "test_perf_user"
        }
    
    start_time = time.time()
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            duration = time.time() - start_time
            print(f"Status: {resp.status_code}")
            print(f"Total Duration: {duration:.2f} seconds")
            
            if resp.status_code == 200:
                data_wrap = resp.json().get("data", {})
                content = data_wrap.get("content", "") or data_wrap.get("response", "")
                if not content and isinstance(data_wrap, str):
                    content = data_wrap
                
                stale_count = content.count("STALE")
                # Also check for "Data Refresh Warning" or "stale" banners
                stale_count += content.count("Data Refresh Warning")
                
                unavailable_count = content.count("Unavailable") + content.count("Failed")
                print(f"Stale/Warning Markers: {stale_count}")
                print(f"Unavailable/Error Markers: {unavailable_count}")
                
                if duration < 12: # Full briefing has 9 tools, parallelized. 12s is a healthy target for real data.
                    print("✅ Performance Target Met")
                else:
                    print(f"⚠️ Duration was {duration:.2f}s")
                    
        except Exception as e:
            print(f"❌ Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_briefing_performance(mode="full"))
    asyncio.run(test_briefing_performance(mode="slim"))
