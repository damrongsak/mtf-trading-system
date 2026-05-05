import asyncio
import os
import aiohttp
import json

# Institutional Auth (simulated or real from env)
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "demo_token") # We need a real token for API Gateway, or call strategy-core directly

async def verify_gamma_endpoint():
    strategy_core_url = "http://localhost:8001/api/v1" # Mapping 8003:8000 in compose for strategy-core
    # Wait, let's check docker-compose ports for host access
    # strategy-core: 8003:8000
    
    url = "http://localhost:8003/api/v1/analysis/gamma/levels"
    params = {"symbol": "XAUUSD", "regime_monitor_mode": "true"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as resp:
                print(f"Strategy Core Response Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    regime = data.get("regime", {})
                    print(f"Regime Valid: {regime.get('is_valid')}")
                    print(f"Integrity Alerts: {regime.get('integrity_alerts')}")
                    print(f"Net GEX: {regime.get('net_gex')}")
                    
                    # Levels check
                    levels = data.get("levels", [])
                    print(f"Total Levels: {len(levels)}")
                    for l in levels[:2]:
                        print(f"Level: {l['strike']} ({l['type']})")
                else:
                    print(f"Error: {await resp.text()}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_gamma_endpoint())
