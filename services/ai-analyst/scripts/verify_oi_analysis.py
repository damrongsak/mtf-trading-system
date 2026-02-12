
import asyncio
import httpx
import json
import time

API_URL = "http://localhost:8000/api/v1/data/open-interest/analysis"

async def verify_analysis():
    print(f"--- Verifying OI Analysis & Caching ---")
    
    # 1. Fetch Latest Snapshot Date first to be sure
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:8000/api/v1/data/open-interest/snapshots?limit=1")
        if r.status_code != 200:
            print("Failed to fetch snapshots")
            return
        snapshot_at = r.json()['data'][0]['snapshot_at']
        print(f"Latest Snapshot: {snapshot_at}")
        
        params = {"snapshot_at": snapshot_at}
        
        # 2. First Call (Cache Miss)
        start_time = time.time()
        r1 = await client.get(API_URL, params=params)
        duration_1 = time.time() - start_time
        
        if r1.status_code != 200:
            print(f"R1 Failed: {r1.status_code} {r1.text}")
            return
            
        data1 = r1.json()['data']
        oiwap = data1['summary'].get('oiwap')
        print(f"R1 (Cache Miss) Duration: {duration_1:.4f}s")
        print(f"OIWAP Value: {oiwap}")
        
        if oiwap is not None and oiwap > 0:
            print("✅ OIWAP is present and > 0")
        else:
            print("❌ OIWAP missing or 0")
            
        # 3. Second Call (Cache Hit)
        start_time = time.time()
        r2 = await client.get(API_URL, params=params)
        duration_2 = time.time() - start_time
        
        print(f"R2 (Cache Hit)  Duration: {duration_2:.4f}s")
        
        # Expectation: R2 < R1 significantly
        if duration_2 < duration_1:
             print(f"✅ Latency Improved: {duration_1/duration_2:.1f}x faster")
        else:
             print("⚠️ Latency not improved (Might be local network noise or fast DB)")

if __name__ == "__main__":
    asyncio.run(verify_analysis())
