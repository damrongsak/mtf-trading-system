import aiohttp
import asyncio
import sys

async def verify():
    print("--- Verifying Real Sentiment Flow (AI Analyst -> Data Pipeline) ---")
    
    async with aiohttp.ClientSession() as session:
        # 1. Trigger Analysis (Local call to AI Analyst)
        print("\n[1] Triggering Analysis for XAU/USD...")
        url = "http://localhost:8000/analyze/sentiment"
        payload = {"symbol": "XAU/USD", "context": "verification"}
        
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Analysis Success:")
                    print(f"   Score: {data.get('score')}")
                    print(f"   Reason: {data.get('reason')}")
                else:
                    print(f"❌ Failed to analyze: {resp.status} {await resp.text()}")
                    return
        except Exception as e:
            print(f"❌ Connection Error (AI Analyst): {e}")
            return

        # 2. Verify Persistence (Call Data Pipeline)
        print("\n[2] Verifying Persistence in Data Pipeline...")
        # Note: In docker network, hostname is 'data-pipeline'
        dp_url = "http://data-pipeline:8000/api/v1/news/sentiment/history"
        params = {"symbol": "XAU/USD"}
        
        try:
            async with session.get(dp_url, params=params) as resp:
                 if resp.status == 200:
                     history = await resp.json()
                     if history:
                         latest = history[0]
                         print(f"✅ Data Pipeline Record Found:")
                         print(f"   ID: {latest['id']}")
                         print(f"   Score: {latest['score']}")
                         print(f"   Saved At: {latest['created_at']}")
                         print("\nSUCCESS: End-to-End Flow Verified with Real Data.")
                     else:
                         print("❌ No history found in Data Pipeline. Persistence failed.")
                 else:
                     print(f"❌ Failed to fetch history: {resp.status} {await resp.text()}")
        except Exception as e:
            print(f"❌ Connection Error (Data Pipeline): {e}")

if __name__ == "__main__":
    asyncio.run(verify())
