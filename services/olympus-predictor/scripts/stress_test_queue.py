import asyncio
import json
import uuid
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis.asyncio as redis
from src.app.core.config import settings

async def stress_test_queue(n=5):
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    queue_name = "queue:predictor:training"
    
    print(f"🚀 Pushing {n} training jobs to {queue_name}...")
    
    job_ids = []
    for i in range(n):
        job_id = str(uuid.uuid4())
        payload = {
            "job_id": job_id,
            "symbol": "XAUUSD",
            "lookback": 500 + (i * 100), # Smaller lookback for faster test
            "macro_lookback": 30
        }
        
        await r.set(f"job:{job_id}:status", "queued", ex=3600)
        await r.lpush(queue_name, json.dumps(payload))
        job_ids.append(job_id)
        print(f"  [+] Job {job_id} queued")

    print("\n⏳ Monitoring jobs...")
    completed = 0
    failed = 0
    
    # Track original list for monitoring
    monitor_ids = list(job_ids)
    
    while completed + failed < n:
        to_remove = []
        for jid in monitor_ids:
            status = await r.get(f"job:{jid}:status")
            if status == "completed":
                completed += 1
                to_remove.append(jid)
                print(f"  [✔] Job {jid} COMPLETED")
            elif status == "failed":
                failed += 1
                to_remove.append(jid)
                err = await r.get(f"job:{jid}:error")
                print(f"  [✖] Job {jid} FAILED: {err}")
        
        for jid in to_remove:
            monitor_ids.remove(jid)
            
        if completed + failed < n:
            await asyncio.sleep(5)
            print(f"Progress: {completed + failed}/{n} processed...")

    print(f"\n✅ Stress Test Finished. Success: {completed}, Failed: {failed}")

if __name__ == "__main__":
    asyncio.run(stress_test_queue(3))
