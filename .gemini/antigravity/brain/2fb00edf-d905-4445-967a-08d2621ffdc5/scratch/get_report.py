import httpx
import asyncio

async def get_full_report():
    gateway_url = "http://localhost:8000/api/v1"
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Auth
        auth_resp = await client.post(f"{gateway_url}/auth/token", data={"username": "trader1", "password": "password123"})
        data = auth_resp.json()
        token = data.get("access_token") or data.get("auth", {}).get("access_token")
        
        # Briefing
        r = await client.get(f"{gateway_url}/ai/briefing", headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            print(r.json()["data"]["content"])

if __name__ == "__main__":
    asyncio.run(get_full_report())
