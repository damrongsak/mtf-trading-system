
import asyncio
import httpx
import json
import time
import os

# Inside container, localhost:8000 is the service itself
API_URL = "http://127.0.0.1:8000/api/v1/data/open-interest/analysis"
SNAPSHOT_URL = "http://127.0.0.1:8000/api/v1/data/open-interest/snapshots"

async def verify_analysis():
    print(f"--- Verifying OI Analysis & Caching (Internal) ---")
    
    async with httpx.AsyncClient() as client:
        # 1. Fetch Latest Snapshot
        try:
            r = await client.get(f"{SNAPSHOT_URL}?limit=1", timeout=5.0)
            if r.status_code != 200:
                print(f"Failed to fetch snapshots: {r.status_code}")
                return
            
            data = r.json().get('data', [])
            if not data:
                print("No snapshots found")
                return
                
            snapshot_at = data[0]['snapshot_at']
            print(f"Latest Snapshot: {snapshot_at}")
        except Exception as e:
            print(f"Connection failed: {e}")
            return
        
        params = {"snapshot_at": snapshot_at}
        
        # 2. First Call (Cache Miss - or Hit if I just ran it?)
        # To guarantee Miss, I'd need to change params, but I want to verify OIWAP on the main snapshot.
        # I'll rely on the logs printed by the service (I can't see them here easily without docker logs)
        # OR I can just look at latency drop.
        
        print("Sending Request 1...")
        start_time = time.time()
        r1 = await client.get(API_URL, params=params, timeout=30.0)
        duration_1 = time.time() - start_time
        
        if r1.status_code != 200:
            print(f"R1 Failed: {r1.status_code} {r1.text}")
            return
            
        data1 = r1.json()['data']
        summary = data1.get('summary', {})
        oiwap = summary.get('oiwap')
        
        print(f"R1 Duration: {duration_1:.4f}s")
        print(f"OIWAP Value: {oiwap}")
        
        if oiwap is not None and oiwap > 0:
            print("✅ OIWAP is present and > 0")
        else:
            print("❌ OIWAP missing or 0")
            print(f"Summary keys: {summary.keys()}")
            
        # 3. Second Call (Should be Cache Hit)
        print("Sending Request 2...")
        start_time = time.time()
        r2 = await client.get(API_URL, params=params, timeout=10.0)
        duration_2 = time.time() - start_time
        
        print(f"R2 Duration: {duration_2:.4f}s")
        
        if duration_2 < duration_1:
             print(f"✅ Latency Improved: {duration_1/duration_2:.1f}x faster")
        else:
             print("⚠️ Latency similar (Maybe already cached or fast DB)")

if __name__ == "__main__":
    asyncio.run(verify_analysis())
