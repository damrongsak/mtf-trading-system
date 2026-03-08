
import asyncio
import httpx
import json
import os

API_URL = os.getenv("API_URL", "http://api-gateway:8000")

async def main():
    async with httpx.AsyncClient() as client:
        # Login
        resp = await client.post(f"{API_URL}/api/v1/auth/token", data={"username": "trader1@mtf-olympus.com", "password": "password123"})
        token = resp.json()["auth"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get Latest Snapshot
        resp = await client.get(f"{API_URL}/api/v1/data/open-interest/snapshots?limit=1", headers=headers)
        print("Snapshots:", resp.text)
        snapshots = resp.json()
        if isinstance(snapshots, dict) and "data" in snapshots:
             snapshots = snapshots["data"]
        
        snap = snapshots[0]["snapshot_at"]
        print(f"Using Snapshot: {snap}")
        
        # Get Analysis
        resp = await client.get(f"{API_URL}/api/v1/data/open-interest/analysis", params={"snapshot_at": snap}, headers=headers)
        print("\nAnalysis Raw JSON:")
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
